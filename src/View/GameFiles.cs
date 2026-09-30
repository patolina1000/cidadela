using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>Caminhos dos JSON de dados e carga do <see cref="GameData"/>, para as cenas que não são o jogo (menu, biografia, estresse).</summary>
public static class GameFiles
{
    public const string Items = "res://data/items.json";
    public const string Resources = "res://data/resources.json";
    public const string Castellan = "res://data/castellan.json";
    public const string Villagers = "res://data/villagers.json";
    public const string Buildings = "res://data/buildings.json";
    public const string Recipes = "res://data/recipes.json";
    public const string Terrain = "res://data/terrain.json";
    public const string VillagerStatus = "res://data/villager_status.json";
    public const string Litanies = "res://data/ladainhas.json";

    /// <summary>Onde o jogo salvo ficaria. Ainda não existe sistema de save (27/09/2026): o menu só olha se o arquivo existe.</summary>
    public const string SavePath = "user://save.json";

    public const string MenuScene = "res://scenes/Menu.tscn";
    public const string GameScene = "res://scenes/Main.tscn";
    public const string BiographyScene = "res://scenes/Biography.tscn";

    public static GameData LoadData() => GameData.Parse(
        FileAccess.GetFileAsString(Items),
        FileAccess.GetFileAsString(Resources),
        FileAccess.GetFileAsString(Castellan),
        FileAccess.GetFileAsString(Villagers),
        FileAccess.GetFileAsString(Buildings),
        FileAccess.GetFileAsString(Recipes),
        FileAccess.GetFileAsString(Terrain));

    public static bool HasSave() => FileAccess.FileExists(SavePath);
}
