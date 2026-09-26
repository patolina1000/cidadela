using System;
using System.IO;
using System.Numerics;

namespace Cidadela.Simulation.Tests;

/// <summary>Monta mundos pequenos a partir de JSON, pelo mesmo caminho que o jogo usa.</summary>
internal static class TestWorlds
{
    public const string Resources = """
        {
          "wood":  { "name": "Madeira", "gatherSeconds": 1.0, "amount": 30 },
          "stone": { "name": "Pedra",   "gatherSeconds": 1.5, "amount": 2 }
        }
        """;

    public const string CastellanStats = """{ "speed": 6.0, "reach": 10.0, "radius": 0.3 }""";

    public static GameData Data() => GameData.Parse(Resources, CastellanStats);

    /// <summary>Mapa 20×20 com o Castelão em (x, z) e os recursos dados como JSON.</summary>
    public static SimWorld Open(int x = 3, int z = 3, string resources = "[]") =>
        MapLoader.Parse($$"""
            { "width": 20, "height": 20,
              "castellan": { "x": {{x}}, "z": {{z}} },
              "resources": {{resources}} }
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
