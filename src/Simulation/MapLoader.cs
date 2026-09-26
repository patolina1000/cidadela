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
    public static SimWorld Parse(string json, GameData gameData)
    {
        MapData data = JsonSerializer.Deserialize<MapData>(json, GameData.JsonOptions)
            ?? throw new FormatException("Mapa vazio.");

        var world = new SimWorld(new WorldGrid(data.Width, data.Height), gameData);

        if (data.Castellan is null)
            throw new FormatException("Mapa sem o Castelão.");
        GridPos start = Checked(world, data.Castellan.X, data.Castellan.Z);
        world.SetCastellan(new System.Numerics.Vector2(start.X, start.Z));

        foreach (PlacedData r in data.Resources)
            world.AddResource(r.Kind, Checked(world, r.X, r.Z));

        foreach (PlacedData m in data.Machines)
            world.AddMachine(m.Kind, Checked(world, m.X, m.Z));

        foreach (VillagerData v in data.Villagers)
        {
            if (v.Path.Count == 0)
                throw new FormatException("Aldeão sem rota.");
            List<GridPos> path = v.Path.Select(p => Checked(world, p[0], p[1])).ToList();
            world.AddVillager(path, v.Speed);
        }

        return world;
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
        public List<PlacedData> Machines { get; set; } = new();
        public List<VillagerData> Villagers { get; set; } = new();
    }

    private sealed class PlacedData
    {
        public string Kind { get; set; } = "";
        public int X { get; set; }
        public int Z { get; set; }
    }

    private sealed class CastellanData
    {
        public int X { get; set; }
        public int Z { get; set; }
    }

    private sealed class VillagerData
    {
        public float Speed { get; set; } = 1f;
        public List<int[]> Path { get; set; } = new();
    }
}
