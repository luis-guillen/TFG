using Microsoft.AspNetCore.Mvc;
using CrawlerWeb.Models;
using CrawlerWeb.Services;

namespace CrawlerWeb.Controllers;

public class HomeController : Controller
{
    private readonly ICrawlerService _crawlerService;

    public HomeController(ICrawlerService crawlerService)
    {
        _crawlerService = crawlerService;
    }

    [HttpGet]
    public IActionResult Index()
    {
        return View(new CrawlViewModel());
    }

    [HttpPost]
    public async Task<IActionResult> Index(CrawlViewModel model)
    {
        if (!ModelState.IsValid)
            return View(model);

        // Asegurar que la URL tiene esquema
        if (!model.Request.Url.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
            !model.Request.Url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            model.Request.Url = "https://" + model.Request.Url;
        }

        model.Result = await _crawlerService.CrawlAsync(model.Request);
        return View(model);
    }
}
