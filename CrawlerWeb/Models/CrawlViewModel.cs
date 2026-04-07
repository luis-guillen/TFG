namespace CrawlerWeb.Models;

/// <summary>
/// ViewModel que combina la petición y el resultado para la vista.
/// </summary>
public class CrawlViewModel
{
    public CrawlerRequest Request { get; set; } = new();
    public CrawlResult? Result { get; set; }
}
