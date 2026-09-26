using System;
using System.IO;
using System.Numerics;

namespace Cidadela.Simulation.Tests;

/// <summary>Monta mundos pequenos a partir de JSON, pelo mesmo caminho que o jogo usa.</summary>
internal static class TestWorlds
{
    public const string Items = """
        {
          "wood":  { "name": "Madeira", "color": "6B5B4B" },
          "stone": { "name": "Pedra",   "color": "A89F91" },
          "shaft": { "name": "Haste",   "color": "C9B38A" }
        }
        """;

    public const string Resources = """
        {
          "wood":  { "gatherSeconds": 1.0, "amount": 30 },
          "stone": { "gatherSeconds": 1.5, "amount": 2 }
        }
        """;

    /// <summary>Serraria de teste: 1 madeira vira 2 hastes em 1 s (20 ticks).</summary>
    public const string Recipes = """
        { "shafts": { "machine": "sawmill", "inputs": { "wood": 1 }, "outputs": { "shaft": 2 }, "seconds": 1 } }
        """;

    /// <summary>Aldeão de teste: 5 células/s, coleta no mesmo tempo que o Castelão, carrega 2.</summary>
    public const string VillagerStats = """{ "speed": 5.0, "gatherMultiplier": 1.0, "carry": 2 }""";

    public const string CastellanStats = """{ "speed": 6.0, "reach": 10.0, "gatherReach": 1.0, "radius": 0.3 }""";

    public const string Buildings = """
        {
          "belt":  { "name": "Esteira", "cost": { "wood": 1 }, "solid": false, "beltSpeed": 1.5 },
          "chest": { "name": "Baú",     "cost": { "wood": 4 }, "solid": true,  "storage": true },
          "sawmill": { "name": "Serraria", "cost": { "wood": 8 }, "solid": true },
          "lumber_hut": { "name": "Cabana do Lenhador", "cost": { "wood": 2 }, "solid": true,
                          "job": { "name": "Lenhador", "resource": "wood", "radius": 8, "capacity": 3 } }
        }
        """;

    public static GameData Data() => GameData.Parse(Items, Resources, CastellanStats, VillagerStats, Buildings, Recipes);

    /// <summary>Mapa 20×20 com o Castelão em (x, z) e os recursos, construções e aldeões dados como JSON.</summary>
    public static SimWorld Open(int x = 3, int z = 3, string resources = "[]", string buildings = "[]",
        string villagers = "[]") =>
        MapLoader.Parse($$"""
            { "width": 20, "height": 20,
              "castellan": { "x": {{x}}, "z": {{z}} },
              "resources": {{resources}},
              "buildings": {{buildings}},
              "villagers": {{villagers}} }
            """, Data());

    public static void Move(SimWorld world, float x, float z, int ticks)
    {
        world.Enqueue(new MoveCommand(new Vector2(x, z)));
        for (int i = 0; i < ticks; i++)
            world.Tick();
    }

    public static void Run(SimWorld world, int ticks)
    {
        for (int i = 0; i < ticks; i++)
            world.Tick();
    }

    public static string DataFile(string relative) =>
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "data", relative));
}
