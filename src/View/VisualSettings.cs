using System.Text.Json;
using Godot;

namespace Cidadela.View;

/// <summary>Parâmetros de desenho de data/visual.json (borda de luz fria), lidos uma vez.</summary>
public sealed class VisualSettings
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
    };

    private static VisualSettings? _current;

    public RimSettings Rim { get; set; } = new();

    public static VisualSettings Current => _current ??=
        JsonSerializer.Deserialize<VisualSettings>(FileAccess.GetFileAsString("res://data/visual.json"), Options) ?? new VisualSettings();

    /// <summary>Liga a borda de luz fria num material do Toon.gdshader com os valores do JSON.</summary>
    public void ApplyRim(ShaderMaterial material)
    {
        material.SetShaderParameter("rim_enabled", true);
        material.SetShaderParameter("rim_color", new Color(Rim.Color));
        material.SetShaderParameter("rim_strength", Rim.Strength);
        material.SetShaderParameter("rim_width", Rim.Width);
    }

    public sealed class RimSettings
    {
        public string Color { get; set; } = "#B8C7E6";
        public float Strength { get; set; } = 0.1f;
        public float Width { get; set; } = 0.144f;
    }
}
