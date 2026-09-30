using System;
using System.Collections.Generic;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Passar no vão entre dois troncos vizinhos (lado a lado e na diagonal), vindo de vários ângulos: a protagonista
/// desliza em volta do tronco sem enroscar, e o aldeão também atravessa (dados de teste com os troncos de data/).
/// </summary>
public class TreeGapTests
{
    private static SimWorld Open(float x, float z, string resources, string buildings = "[]", string villagers = "[]")
    {
        SimWorld world = MapLoader.Parse($$"""
            { "width": 20, "height": 20, "castellan": { "x": 1, "z": 1 }, "resources": {{resources}},
              "buildings": {{buildings}}, "villagers": {{villagers}} }
            """, TrunkTests.TrunkData());
        world.Castellan.PlaceAt(new Vector2(x, z));
        return world;
    }

    private const string SideBySide = """[{ "kind": "wood", "x": 4, "z": 4 }, { "kind": "wood", "x": 5, "z": 4 }]""";
    private const string Diagonal = """[{ "kind": "wood", "x": 4, "z": 4 }, { "kind": "wood", "x": 5, "z": 5 }]""";

    [Theory]
    [InlineData(4.5f, 0f)]    // pelo meio, reto
    [InlineData(4.4f, 0f)]    // um pouco para a esquerda
    [InlineData(4.62f, 0f)]   // um pouco para a direita
    [InlineData(4.5f, 0.35f)] // em diagonal
    [InlineData(4.5f, -0.35f)]
    public void CastellanPassesBetweenSideBySideTrunks(float startX, float sideways)
    {
        SimWorld world = Open(startX, 6.5f, SideBySide);
        TestWorlds.Move(world, sideways, -1f, ticks: 25);
        Assert.True(world.Castellan.Position.Y < 3f, $"parou em {world.Castellan.Position}");
    }

    [Theory]
    [InlineData(1f, -1f)]   // perpendicular ao vão
    [InlineData(1f, -0.6f)] // de viés
    [InlineData(0.6f, -1f)]
    public void CastellanPassesBetweenDiagonalTrunks(float dx, float dz)
    {
        // O vão diagonal fica em volta de (4,5; 4,5); ela vem do sudoeste e sai no nordeste.
        SimWorld world = Open(4.5f - 2f * dx, 4.5f - 2f * dz, Diagonal);
        TestWorlds.Move(world, dx, dz, ticks: 25);
        Vector2 p = world.Castellan.Position;
        Assert.True(p.X > 5.5f && p.Y < 3.5f, $"parou em {p}");
    }

    [Fact]
    public void CastellanStillCannotWalkThroughATrunk()
    {
        SimWorld world = Open(4f, 6.5f, """[{ "kind": "wood", "x": 4, "z": 4 }]""");
        TestWorlds.Move(world, 0f, -1f, ticks: 25);
        // Vindo reto no centro, desliza para um lado e passa; mas nunca fica dentro do tronco.
        Assert.True(Vector2.Distance(world.Castellan.Position, new Vector2(4f, 4f)) >= 0.44f);
    }

    /// <summary>Muro de pedras em z = 4 com duas árvores vizinhas no meio: o único jeito de passar é entre os troncos.</summary>
    private static string WallWith(params (int X, int Z)[] trees)
    {
        var list = new List<string>();
        var treeSet = new HashSet<(int, int)>(trees);
        foreach ((int x, int z) in trees)
            list.Add($$"""{ "kind": "wood", "x": {{x}}, "z": {{z}} }""");
        for (int x = 0; x < 20; x++)
            if (!treeSet.Contains((x, 4)))
                list.Add($$"""{ "kind": "stone", "x": {{x}}, "z": 4 }""");
        return "[" + string.Join(",", list) + "]";
    }

    // O baú fica ao norte do muro e o aldeão nasce ao sul: as árvores do muro são as mais perto, ele as coleta pelo
    // lado sul e, para entregar, precisa atravessar o muro pelo vão entre os troncos.
    [Fact]
    public void VillagerCrossesBetweenSideBySideTrunks()
    {
        SimWorld world = Open(18f, 18f, WallWith((4, 4), (5, 4)),
            buildings: """[{ "kind": "chest", "x": 4, "z": 1 }]""", villagers: """[{ "x": 4, "z": 8 }]""");
        LumberLitany(world, 4, 1);
        TestWorlds.Run(world, 600);
        Assert.True(world.BuildingAt(new GridPos(4, 1))!.Storage!.Count("wood") >= 2,
            $"estado {world.Villagers[0].Status}, em {world.Villagers[0].Position}");
    }

    [Fact]
    public void VillagerCrossesBetweenDiagonalTrunks()
    {
        // Muro em z = 4 com um buraco em (4, 4) fechado por uma árvore, e outra árvore em (5, 5) logo depois.
        SimWorld world = Open(18f, 18f, WallWith((4, 4)).Replace("]", """, { "kind": "wood", "x": 5, "z": 5 }]"""),
            buildings: """[{ "kind": "chest", "x": 6, "z": 1 }]""", villagers: """[{ "x": 7, "z": 8 }]""");
        LumberLitany(world, 6, 1);
        TestWorlds.Run(world, 900);
        Assert.True(world.BuildingAt(new GridPos(6, 1))!.Storage!.Count("wood") >= 2,
            $"estado {world.Villagers[0].Status}, em {world.Villagers[0].Position}");
    }

    [Fact]
    public void VillagerGathersTouchingTheTrunk()
    {
        SimWorld world = Open(18f, 18f, """[{ "kind": "wood", "x": 4, "z": 2 }]""",
            buildings: """[{ "kind": "chest", "x": 4, "z": 6 }]""", villagers: """[{ "x": 4, "z": 7 }]""");
        LumberLitany(world, 4, 6);
        for (int i = 0; i < 300 && world.Villagers[0].Task != VillagerTask.Gathering; i++)
            world.Tick();
        TestWorlds.Run(world, 5);
        Villager v = world.Villagers[0];
        Assert.Equal(VillagerTask.Gathering, v.Task);
        float d = Vector2.Distance(v.Position, new Vector2(4f, 2f));
        Assert.InRange(d, 0.2f, 0.45f); // tronco + corpo do aldeão, não a célula vizinha (1 m)
    }

    /// <summary>O aldeão colhe tora perto do baú e põe nele (o que a cabana de lenhador fazia sozinha antes das ladainhas).</summary>
    private static void LumberLitany(SimWorld world, int x, int z) =>
        TestWorlds.Teach(world, world.Villagers[0], TestWorlds.Litany(TestWorlds.Gather("wood", x, z), TestWorlds.Put("wood", x, z)));
}
