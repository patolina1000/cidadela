using System;
using System.IO;
using System.Numerics;

namespace Cidadela.Simulation.Tests;

/// <summary>Monta mundos pequenos a partir de JSON, pelo mesmo caminho que o jogo usa.</summary>
internal static class TestWorlds
{
    public const string Items = """
        {
          "wood":  { "name": "Madeira", "color": "6B5B4B", "peso": "pesado" },
          "stone": { "name": "Pedra",   "color": "A89F91", "peso": "pesado" },
          "shaft": { "name": "Haste",   "color": "C9B38A", "peso": "leve" }
        }
        """;

    public const string Resources = """
        {
          "wood":  { "gatherSeconds": 1.0, "amount": 30 },
          "stone": { "gatherSeconds": 1.5, "amount": 2 }
        }
        """;

    /// <summary>
    /// Máquinas de teste: serraria (1 madeira → 2 hastes em 1 s, sem postos); forno (10 madeiras → 20 hastes em 120 s, sem
    /// postos); serraria com 2 postos (1 madeira → 2 hastes em 2 s); prensa com 1 posto (1 haste → 1 pedra em 5 s); serraria a mana (gasta 20/s; 1 madeira → 1 haste em 1 s); berço (gasta 20/s; 1 madeira + 1 haste → 1 aldeão em 10 s).
    /// </summary>
    public const string Recipes = """
        {
          "shafts": { "machine": "sawmill",     "inputs": { "wood": 1 },  "outputs": { "shaft": 2 },  "seconds": 1 },
          "kiln":   { "machine": "kiln",        "inputs": { "wood": 10 }, "outputs": { "shaft": 20 }, "seconds": 120 },
          "crewed": { "machine": "crewed_mill", "inputs": { "wood": 1 },  "outputs": { "shaft": 2 },  "seconds": 2 },
          "press":  { "machine": "press",       "inputs": { "shaft": 1 }, "outputs": { "stone": 1 },  "seconds": 5 },
          "powered": { "machine": "powered_mill", "inputs": { "wood": 1 }, "outputs": { "shaft": 1 }, "seconds": 1 },
          "cradle":  { "machine": "cradle", "inputs": { "wood": 1, "shaft": 1 }, "outputs": {}, "seconds": 10 }
        }
        """;

    /// <summary>Aldeão de teste: patamares 5, 6 e 8 células/s, penalidade 2,5 no base (fator 0,5), teto 7; coleta no mesmo tempo que o Castelão, carrega 2 pesados ou 10 leves.</summary>
    public const string VillagerStats = """{ "speedTiers": [5.0, 6.0, 8.0], "penaltySpeed": 2.5, "maxSpeed": 7.0, "gatherMultiplier": 1.0, "carry": { "pesado": 2, "leve": 10 } }""";

    public const string CastellanStats ="""{ "speed": 6.0, "reach": 10.0, "gatherReach": 1.0, "radius": 0.3 }""";

    public const string Buildings = """
        {
          "chest": { "name": "Baú",     "cost": { "wood": 4 }, "solid": true,  "storage": true },
          "sawmill": { "name": "Serraria", "cost": { "wood": 8 }, "solid": true },
          "kiln": { "name": "Forno", "cost": { "wood": 4 }, "solid": true },
          "crewed_mill": { "name": "Serraria com postos", "cost": { "wood": 8 }, "solid": true,
                           "posts": { "count": 2, "name": "Serrador", "tool": "saw" } },
          "press": { "name": "Prensa", "cost": { "wood": 2 }, "solid": true,
                     "posts": { "count": 1, "name": "Prenseiro", "tool": "press" } },
          "carrier_post": { "name": "Posto de Carregadores", "cost": { "wood": 4 }, "solid": true,
                            "carriers": { "count": 2, "radius": 12 } },
          "tower": { "name": "Torre", "cost": { "wood": 1 }, "solid": true, "tower": { "wire": 7, "area": 5 } },
          "generator": { "name": "Gerador", "cost": { "wood": 1 }, "solid": true, "mana": { "supply": 10 } },
          "lamp": { "name": "Lâmpada", "cost": { "wood": 1 }, "solid": true, "mana": { "use": 4 } },
          "powered_mill": { "name": "Serraria a mana", "cost": { "wood": 1 }, "solid": true, "mana": { "use": 20 } },
          "cradle": { "name": "Berço", "cost": { "wood": 1 }, "solid": true, "mana": { "use": 20 }, "spawnsVillager": true },
          "floor": { "name": "Piso de teste", "cost": { "wood": 1 }, "solid": false, "speedBonus": 1.2 },
          "lumber_hut": { "name": "Cabana do Lenhador", "cost": { "wood": 2 }, "solid": true,
                          "job": { "name": "Lenhador", "resource": "wood", "radius": 8, "capacity": 3 } }
        }
        """;

    public static GameData Data() => GameData.Parse(Items, Resources, CastellanStats, VillagerStats, Buildings, Recipes);

    /// <summary>Mapa 20×20 com o Castelão em (x, z) e os recursos, construções e aldeões dados como JSON.</summary>
    public static SimWorld Open(int x = 3, int z = 3, string resources = "[]", string buildings = "[]",
        string villagers = "[]", GameData? data = null, string terrain = "null") =>
        MapLoader.Parse($$"""
            { "width": 20, "height": 20,
              "castellan": { "x": {{x}}, "z": {{z}} },
              "resources": {{resources}},
              "buildings": {{buildings}},
              "villagers": {{villagers}},
              "terrain": {{terrain}} }
            """, data ?? Data());

    /// <summary>Os JSON de verdade de data/ (os números do jogo).</summary>
    public static GameData RealData() => GameData.Parse(DataFile("items.json"), DataFile("resources.json"),
        DataFile("castellan.json"), DataFile("villagers.json"), DataFile("buildings.json"), DataFile("recipes.json"),
        DataFile("terrain.json"));

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
