using CrawlerWeb.Services;

var builder = WebApplication.CreateBuilder(args);

// MVC
builder.Services.AddControllersWithViews();

// HttpClient para el crawler
builder.Services.AddHttpClient("Crawler", client =>
{
    client.DefaultRequestHeaders.Add("User-Agent", "CrawlerWeb/1.0 (TFG; academico)");
    client.DefaultRequestHeaders.Add("Accept", "text/html,application/xhtml+xml");
    client.DefaultRequestHeaders.Add("Accept-Language", "es,en;q=0.5");
    client.Timeout = TimeSpan.FromSeconds(15);
});

// Registrar servicio de crawling
builder.Services.AddScoped<ICrawlerService, CrawlerService>();

var app = builder.Build();

// Solo usar estas opciones en producción
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
    app.UseHttpsRedirection();
}
app.UseRouting();
app.UseAuthorization();
app.MapStaticAssets();
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}")
    .WithStaticAssets();

app.Run();
