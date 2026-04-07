using System.ComponentModel.DataAnnotations;

namespace CrawlerWeb.Models;

/// <summary>
/// Datos del formulario: URL a crawlear y límites.
/// </summary>
public class CrawlerRequest
{
    [Required(ErrorMessage = "La URL es obligatoria.")]
    [Url(ErrorMessage = "Introduce una URL válida (ej: https://ejemplo.com).")]
    [Display(Name = "URL del sitio")]
    public string Url { get; set; } = string.Empty;

    [Range(1, 100, ErrorMessage = "El máximo de páginas debe estar entre 1 y 100.")]
    [Display(Name = "Máximo de páginas")]
    public int MaxPages { get; set; } = 20;

    [Range(1, 5, ErrorMessage = "La profundidad máxima debe estar entre 1 y 5.")]
    [Display(Name = "Profundidad máxima")]
    public int MaxDepth { get; set; } = 2;
}
