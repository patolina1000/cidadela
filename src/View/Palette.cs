using Cidadela.Simulation;
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
    public static readonly Color Sickly = new("9BC53D");

    // Grama do crepúsculo (GDD, seção 17, paleta do dia revisada em 26/09/2026).
    public static readonly Color DeadGrass = new("5A5847");
    public static readonly Color GrayMoss = new("4E5544");
    public static readonly Color PurpleLichen = new("6B4F7C");

    /// <summary>Fora da paleta do GDD: só para avisos de interface (ex.: fora do alcance).</summary>
    public static readonly Color Warning = new("C8402F");

    /// <summary>Cor de um item, vinda de data/items.json.</summary>
    public static Color ForItem(GameData data, string kind) => new(data.Item(kind).Color);
}
