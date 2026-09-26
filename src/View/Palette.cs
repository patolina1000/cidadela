using Godot;

namespace Cidadela.View;

/// <summary>Cores da paleta do GDD (seção 17), usadas enquanto não há arte.</summary>
public static class Palette
{
    public static readonly Color Wood = new("6B5B4B");
    public static readonly Color Moss = new("7A8B5A");
    public static readonly Color Stone = new("A89F91");
    public static readonly Color Wheat = new("C9B38A");
    public static readonly Color DeepPurple = new("2B2140");
    public static readonly Color Midnight = new("1E2A3A");
    public static readonly Color Pumpkin = new("E07B2E");
    public static readonly Color Bone = new("EDE6D6");

    /// <summary>Fora da paleta do GDD: só para avisos de interface (ex.: fora do alcance).</summary>
    public static readonly Color Warning = new("C8402F");

    public static Color ForResource(string kind) => kind switch
    {
        "wood" => Wood,
        "stone" => Stone,
        "iron" => Midnight,
        _ => Colors.Magenta,
    };
}
