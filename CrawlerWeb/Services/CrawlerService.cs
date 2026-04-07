using System.Text;
using System.Text.RegularExpressions;
using CrawlerWeb.Models;
using HtmlAgilityPack;

namespace CrawlerWeb.Services;

/// <summary>
/// Servicio de crawling BFS que recorre páginas internas de un dominio,
/// extrae texto limpio y lo guarda en archivos .txt.
/// </summary>
public class CrawlerService : ICrawlerService
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<CrawlerService> _logger;

    public CrawlerService(IHttpClientFactory httpClientFactory, ILogger<CrawlerService> logger)
    {
        _httpClientFactory = httpClientFactory;
        _logger = logger;
    }

    public async Task<CrawlResult> CrawlAsync(CrawlerRequest request)
    {
        var result = new CrawlResult();
        var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        // Cola BFS: (url, profundidad)
        var queue = new Queue<(string Url, int Depth)>();

        // Normalizar la URL inicial
        var startUri = new Uri(request.Url);
        var startUrl = NormalizeUrl(startUri);
        queue.Enqueue((startUrl, 0));

        // Crear carpeta de salida
        var domain = startUri.Host.Replace("www.", "");
        var outputPath = Path.Combine(Directory.GetCurrentDirectory(), "Output", domain);
        Directory.CreateDirectory(outputPath);
        result.OutputFolder = outputPath;

        var client = _httpClientFactory.CreateClient("Crawler");

        while (queue.Count > 0 && result.VisitedPages < request.MaxPages)
        {
            var (currentUrl, depth) = queue.Dequeue();

            // Saltar si ya fue visitada
            if (!visited.Add(currentUrl))
                continue;

            _logger.LogInformation("Visitando [{Depth}]: {Url}", depth, currentUrl);

            try
            {
                // Descargar la página
                var response = await client.GetAsync(currentUrl);

                if (!response.IsSuccessStatusCode)
                {
                    result.Errors.Add($"HTTP {(int)response.StatusCode} en {currentUrl}");
                    continue;
                }

                // Solo procesar HTML
                var contentType = response.Content.Headers.ContentType?.MediaType ?? "";
                if (!contentType.Contains("text/html", StringComparison.OrdinalIgnoreCase))
                    continue;

                result.VisitedPages++;
                var html = await response.Content.ReadAsStringAsync();

                // Parsear HTML
                var doc = new HtmlDocument();
                doc.LoadHtml(html);

                // Extraer texto limpio y guardarlo
                var cleanText = ExtractCleanText(doc);
                if (!string.IsNullOrWhiteSpace(cleanText))
                {
                    var fileName = GenerateSafeFileName(currentUrl) + ".txt";
                    var filePath = Path.Combine(outputPath, fileName);
                    await File.WriteAllTextAsync(filePath, cleanText, Encoding.UTF8);
                    result.SavedFiles++;
                    result.SavedFileNames.Add(fileName);
                }

                // Extraer enlaces internos si no hemos llegado a la profundidad máxima
                if (depth < request.MaxDepth)
                {
                    var links = ExtractInternalLinks(doc, startUri);
                    foreach (var link in links)
                    {
                        if (!visited.Contains(link))
                            queue.Enqueue((link, depth + 1));
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error procesando {Url}", currentUrl);
                result.Errors.Add($"Error en {currentUrl}: {ex.Message}");
            }
        }

        _logger.LogInformation(
            "Crawling completado: {Visited} páginas visitadas, {Saved} archivos guardados",
            result.VisitedPages, result.SavedFiles);

        return result;
    }

    /// <summary>
    /// Normaliza una URL: esquema + host + path sin fragmento ni trailing slash.
    /// </summary>
    private static string NormalizeUrl(Uri uri)
    {
        var normalized = $"{uri.Scheme}://{uri.Host}{uri.AbsolutePath}";
        // Quitar trailing slash excepto en la raíz
        if (normalized.EndsWith('/') && uri.AbsolutePath != "/")
            normalized = normalized.TrimEnd('/');
        return normalized;
    }

    /// <summary>
    /// Extrae todos los enlaces internos (mismo host) de un documento HTML.
    /// </summary>
    private static List<string> ExtractInternalLinks(HtmlDocument doc, Uri baseUri)
    {
        var links = new List<string>();
        var anchorNodes = doc.DocumentNode.SelectNodes("//a[@href]");

        if (anchorNodes == null)
            return links;

        foreach (var node in anchorNodes)
        {
            var href = node.GetAttributeValue("href", "").Trim();

            // Ignorar enlaces vacíos, anclas, mailto y javascript
            if (string.IsNullOrEmpty(href) ||
                href.StartsWith('#') ||
                href.StartsWith("mailto:", StringComparison.OrdinalIgnoreCase) ||
                href.StartsWith("javascript:", StringComparison.OrdinalIgnoreCase) ||
                href.StartsWith("tel:", StringComparison.OrdinalIgnoreCase))
                continue;

            // Resolver URL relativa
            if (Uri.TryCreate(baseUri, href, out var absoluteUri))
            {
                // Solo enlaces del mismo host
                if (absoluteUri.Host.Equals(baseUri.Host, StringComparison.OrdinalIgnoreCase))
                {
                    // Ignorar archivos no-HTML comunes
                    var path = absoluteUri.AbsolutePath.ToLower();
                    if (path.EndsWith(".pdf") || path.EndsWith(".jpg") || path.EndsWith(".png") ||
                        path.EndsWith(".gif") || path.EndsWith(".zip") || path.EndsWith(".mp3") ||
                        path.EndsWith(".mp4") || path.EndsWith(".css") || path.EndsWith(".js"))
                        continue;

                    links.Add(NormalizeUrl(absoluteUri));
                }
            }
        }

        return links;
    }

    /// <summary>
    /// Extrae texto legible del HTML, eliminando scripts, estilos y navegación.
    /// </summary>
    private static string ExtractCleanText(HtmlDocument doc)
    {
        // Eliminar nodos que no aportan contenido útil
        var nodesToRemove = doc.DocumentNode.SelectNodes(
            "//script | //style | //noscript | //nav | //header | //footer | //iframe | //svg");

        if (nodesToRemove != null)
        {
            foreach (var node in nodesToRemove)
                node.Remove();
        }

        // Obtener el título
        var titleNode = doc.DocumentNode.SelectSingleNode("//title");
        var title = titleNode != null ? HtmlEntity.DeEntitize(titleNode.InnerText).Trim() : "";

        // Intentar extraer del contenido principal (article, main) o del body
        var contentNode = doc.DocumentNode.SelectSingleNode("//article")
                       ?? doc.DocumentNode.SelectSingleNode("//main")
                       ?? doc.DocumentNode.SelectSingleNode("//body");

        if (contentNode == null)
            return string.Empty;

        // Extraer texto con estructura de bloques
        var sb = new StringBuilder();
        if (!string.IsNullOrEmpty(title))
            sb.AppendLine(title).AppendLine(new string('=', title.Length)).AppendLine();

        ExtractTextRecursive(contentNode, sb);

        // Limpiar espacios en blanco excesivos
        var text = sb.ToString();
        text = Regex.Replace(text, @"[ \t]+", " ");           // múltiples espacios → uno
        text = Regex.Replace(text, @"\n{3,}", "\n\n");         // más de 2 saltos → 2
        text = text.Trim();

        return text;
    }

    /// <summary>
    /// Recorre recursivamente el DOM extrayendo texto con saltos de línea para bloques.
    /// </summary>
    private static void ExtractTextRecursive(HtmlNode node, StringBuilder sb)
    {
        // Nodos de texto
        if (node.NodeType == HtmlNodeType.Text)
        {
            var text = HtmlEntity.DeEntitize(node.InnerText);
            if (!string.IsNullOrWhiteSpace(text))
                sb.Append(text.Trim()).Append(' ');
            return;
        }

        // Elementos de bloque que generan saltos de línea
        var blockElements = new HashSet<string>
        {
            "p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "tr", "blockquote", "section", "article", "aside",
            "pre", "ul", "ol", "dl", "dt", "dd", "figcaption"
        };

        var isBlock = blockElements.Contains(node.Name.ToLower());

        if (isBlock)
            sb.AppendLine();

        foreach (var child in node.ChildNodes)
            ExtractTextRecursive(child, sb);

        if (isBlock)
            sb.AppendLine();
    }

    /// <summary>
    /// Genera un nombre de archivo seguro a partir de una URL.
    /// </summary>
    private static string GenerateSafeFileName(string url)
    {
        var uri = new Uri(url);
        var path = uri.AbsolutePath.Trim('/');

        if (string.IsNullOrEmpty(path))
            return "index";

        // Reemplazar caracteres no válidos
        var safe = Regex.Replace(path, @"[^a-zA-Z0-9_\-]", "_");

        // Limitar longitud
        if (safe.Length > 100)
            safe = safe[..100];

        return safe;
    }
}
