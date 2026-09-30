using System.Text.Json;
using Godot;

namespace Cidadela.View;

/// <summary>Parâmetros de desenho de data/visual.json (borda de luz fria, esmaecer o que tapa personagem, ícones dos aldeões), lidos uma vez.</summary>
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
    public OcclusionSettings Occlusion { get; set; } = new();
    public IconSettings VillagerIcon { get; set; } = new();

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

    /// <summary>Liga o esmaecimento do que tapa a protagonista num material do Toon.gdshader.</summary>
    public void ApplyOcclusion(ShaderMaterial material)
    {
        material.SetShaderParameter("occlusion_enabled", true);
        material.SetShaderParameter("occlusion_radius", Occlusion.Radius);
        material.SetShaderParameter("occlusion_keep", Occlusion.Keep);
        material.SetShaderParameter("occlusion_softness", Occlusion.Softness);
    }

    public sealed class IconSettings
    {
        public float Height { get; set; } = 0.62f;
        public float WorldSize { get; set; } = 0.3f;
        public float MinPx { get; set; } = 26f;
        public float MaxPx { get; set; } = 44f;
        public float ReferenceHeight { get; set; } = 1890f;
    }

    public sealed class OcclusionSettings
    {
        public float Radius { get; set; } = 0.6f;
        public float Keep { get; set; } = 0.35f;
        public float Softness { get; set; } = 0.3f;
        public float ChestHeight { get; set; } = 0.45f;
    }

    public sealed class RimSettings
    {
        public string Color { get; set; } = "#B8C7E6";
        public float Strength { get; set; } = 0.1f;
        public float Width { get; set; } = 0.144f;
    }
}
