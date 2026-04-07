using CrawlerWeb.Models;

namespace CrawlerWeb.Services;

/// <summary>
/// Interfaz del servicio de crawling.
/// </summary>
public interface ICrawlerService
{
    /// <summary>
    /// Ejecuta el crawling a partir de la URL indicada.
    /// </summary>
    Task<CrawlResult> CrawlAsync(CrawlerRequest request);
}
