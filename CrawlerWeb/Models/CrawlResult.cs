namespace CrawlerWeb.Models;

/// <summary>
/// Resultado del proceso de crawling.
/// </summary>
public class CrawlResult
{
    public int VisitedPages { get; set; }
    public int SavedFiles { get; set; }
    public List<string> Errors { get; set; } = new();
    public string OutputFolder { get; set; } = string.Empty;
    public List<string> SavedFileNames { get; set; } = new();
}
