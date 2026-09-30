using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>
/// Monta um <see cref="SimWorld"/> a partir do JSON de mapa. Recebe o texto, não o caminho,
/// para não depender do sistema de arquivos do Godot (res://).
/// </summary>
public static class MapLoader
{
    /// <summary>
    /// <paramref name="litanies"/>: as ladainhas que os aldeões do mapa podem carregar ("litany": "nome" no aldeão).
    /// </summary>
    public static SimWorld Parse(string json, GameData gameData, LitanyLibrary? litanies = null)
    {
        MapData data = JsonSerializer.Deserialize<MapData>(json, GameData.JsonOptions)
            ?? throw new FormatException("Mapa vazio.");

        var world = new SimWorld(new WorldGrid(data.Width, data.Height), gameData) { FreeMachines = data.FreeMachines };
        PaintTerrain(world.Grid, data.Terrain, gameData);

        if (data.Castellan is null)
            throw new FormatException("Mapa sem o Castelão.");
        GridPos start = Checked(world, data.Castellan.X, data.Castellan.Z);
        world.SetCastellan(new System.Numerics.Vector2(start.X, start.Z));
        foreach ((string kind, int amount) in data.Castellan.Items)
            world.Castellan.Inventory.Add(gameData.Item(kind).Kind, amount);

        foreach (PlacedData r in data.Resources)
            world.AddResource(r.Kind, Checked(world, r.X, r.Z));

        foreach (PlacedData b in data.Buildings)
        {
            Building building = world.AddBuilding(gameData.Building(b.Kind), Checked(world, b.X, b.Z), DirectionExtensions.Parse(b.Direction));
            // Baú ou máquina que já começa com itens (mapas de teste): "items": { "wood": 30 }. Na máquina, vão para a
            // entrada (o Relicário começando com fragmentos puros).
            foreach ((string kind, int amount) in b.Items)
                (building.Storage ?? building.Machine?.Input ?? throw new FormatException($"\"{b.Kind}\" não guarda itens."))
                    .Add(gameData.Item(kind).Kind, amount);
        }

        var withLitany = new List<(Villager, Litany)>();
        foreach (PlacedData v in data.Villagers)
        {
            GridPos cell = Checked(world, v.X, v.Z);
            Villager villager = world.AddVillager(new System.Numerics.Vector2(cell.X, cell.Z));
            if (v.Litany is string name)
                withLitany.Add((villager, (litanies ?? LitanyLibrary.Empty)[name]));
        }
        foreach ((Villager villager, Litany litany) in withLitany)
            if (villager.Learn(world, litany) is var fit && fit != LitanyFit.Ok)
                throw new FormatException($"Aldeão em ({villager.Cell.X}, {villager.Cell.Z}) recusa a ladainha \"{litany.Name}\": {fit}.");

        return world;
    }

    /// <summary>
    /// Terreno: um padrão para o mapa todo e manchas por cima, na ordem do arquivo (a última vence).
    /// Mancha com "radius" é um círculo em volta da célula; com "width" e "height", um retângulo a
    /// partir dela. As bordas orgânicas são trabalho do desenho, não do dado.
    /// </summary>
    private static void PaintTerrain(WorldGrid grid, TerrainData? terrain, GameData gameData)
    {
        if (terrain is null)
            return;
        int fill = gameData.Terrain(terrain.Default ?? gameData.Terrains[0].Kind).Index;
        for (int z = 0; z < grid.Height; z++)
            for (int x = 0; x < grid.Width; x++)
                grid.SetTerrain(new GridPos(x, z), fill);

        foreach (PatchData patch in terrain.Patches)
        {
            int index = gameData.Terrain(patch.Kind).Index;
            for (int z = 0; z < grid.Height; z++)
                for (int x = 0; x < grid.Width; x++)
                {
                    bool inside = patch.Radius is float radius
                        ? (x - patch.X) * (x - patch.X) + (z - patch.Z) * (z - patch.Z) <= radius * radius
                        : x >= patch.X && z >= patch.Z && x < patch.X + patch.Width && z < patch.Z + patch.Height;
                    if (inside)
                        grid.SetTerrain(new GridPos(x, z), index);
                }
        }
    }

    private static GridPos Checked(SimWorld world, int x, int z)
    {
        var pos = new GridPos(x, z);
        if (!world.Grid.InBounds(pos))
            throw new FormatException($"Célula fora do mapa: ({x}, {z}).");
        return pos;
    }

    private sealed class MapData
    {
        public int Width { get; set; }
        public int Height { get; set; }
        public CastellanData? Castellan { get; set; }
        public List<PlacedData> Resources { get; set; } = new();
        public List<PlacedData> Buildings { get; set; } = new();
        public List<PlacedData> Villagers { get; set; } = new();
        public TerrainData? Terrain { get; set; }
        /// <summary>Vitrine (palco da Biografia): máquinas sem postos e esteiras sem manivela.</summary>
        public bool FreeMachines { get; set; }
    }

    private sealed class TerrainData
    {
        public string? Default { get; set; }
        public List<PatchData> Patches { get; set; } = new();
    }

    private sealed class PatchData
    {
        public string Kind { get; set; } = "";
        public int X { get; set; }
        public int Z { get; set; }
        public float? Radius { get; set; }
        public int Width { get; set; }
        public int Height { get; set; }
    }

    private sealed class PlacedData
    {
        public string Kind { get; set; } = "";
        public int X { get; set; }
        public int Z { get; set; }
        public string? Direction { get; set; }
        public Dictionary<string, int> Items { get; set; } = new();
        /// <summary>Aldeão: a ladainha que ele já carrega (data/ladainhas.json).</summary>
        public string? Litany { get; set; }
    }

    private sealed class CastellanData
    {
        public int X { get; set; }
        public int Z { get; set; }
        /// <summary>O que ele já leva na mochila (mapas de teste).</summary>
        public Dictionary<string, int> Items { get; set; } = new();
    }
}
