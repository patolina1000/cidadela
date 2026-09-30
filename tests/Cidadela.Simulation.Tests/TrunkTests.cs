using System;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Árvore bloqueia só o tronco (data/resources.json, trunkRadius 0,2); pedra continua bloqueando a célula.</summary>
public class TrunkTests
{
    // Os dados de teste com o tronco da árvore e o alcance até ele iguais aos de data/.
    internal static GameData TrunkData() => GameData.Parse(TestWorlds.Items,
        TestWorlds.Resources.Replace("\"amount\": 30 }", "\"amount\": 30, \"trunkRadius\": 0.2 }"),
        TestWorlds.CastellanStats.Replace("\"radius\": 0.3", "\"radius\": 0.3, \"gatherTrunkReach\": 1.3"),
        TestWorlds.VillagerStats, TestWorlds.Buildings, TestWorlds.Recipes);

    private static SimWorld Open(int x, int z, string resources) => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": {{x}}, "z": {{z}} }, "resources": {{resources}} }
        """, TrunkData());

    private static float TrunkDistance(SimWorld world, GridPos cell) =>
        Vector2.Distance(world.Castellan.Position, new Vector2(cell.X, cell.Z));

    [Fact]
    public void WalkingIntoATreeStopsAtTheTrunkNotAtTheCellEdge()
    {
        SimWorld world = Open(4, 2, """[{ "kind": "wood", "x": 4, "z": 4 }]""");
        TestWorlds.Move(world, 0f, 1f, ticks: 60);
        float d = TrunkDistance(world, new GridPos(4, 4));
        // Corpo 0,3 + tronco 0,2: para a ~0,5 m do centro do tronco (antes parava a 0,8, na borda da célula).
        Assert.InRange(d, 0.49f, 0.62f);
    }

    [Fact]
    public void AStoneStillBlocksTheWholeCell()
    {
        SimWorld world = Open(4, 2, """[{ "kind": "stone", "x": 4, "z": 4 }]""");
        TestWorlds.Move(world, 0f, 1f, ticks: 60);
        Assert.True(TrunkDistance(world, new GridPos(4, 4)) >= 0.79f);
    }

    [Fact]
    public void ThePlayerCanWalkPastTheTrunkInsideTheTreeCell()
    {
        // Sobe 0,6 (6 cél/s × 2 ticks): o corpo invade 0,2 m a célula da árvore (a célula inteira bloquearia) e fica a
        // 0,6 m do centro do tronco (> 0,3 + 0,2). Andando para leste, passa sob a copa sem bater no tronco.
        SimWorld world = Open(2, 4, """[{ "kind": "wood", "x": 4, "z": 4 }]""");
        TestWorlds.Move(world, 0f, -1f, ticks: 2);
        TestWorlds.Move(world, 1f, 0f, ticks: 40);
        Assert.True(world.Castellan.Position.X > 5f);
    }

    [Theory]
    [InlineData(5, 4, true)]  // de lado
    [InlineData(5, 5, true)]  // na diagonal
    [InlineData(6, 4, false)] // duas células
    public void GatherReachIsCountedToTheTrunk(int x, int z, bool can)
    {
        SimWorld world = Open(4, 4, $$"""[{ "kind": "wood", "x": {{x}}, "z": {{z}} }]""");
        ResourceNode tree = world.ResourceAt(new GridPos(x, z))!;
        Assert.Equal(can, world.Castellan.CanGather(tree.Cell, tree.Type.TrunkRadius));
    }

    [Fact]
    public void ATrunkWiderThanTheCellIsRejected()
    {
        string resources = System.Text.RegularExpressions.Regex.Replace(TestWorlds.DataFile("resources.json"),
            "\"trunkRadius\": [0-9.]+", "\"trunkRadius\": 0.7");
        Assert.Throws<FormatException>(() => GameData.Parse(
            TestWorlds.DataFile("items.json"), resources, TestWorlds.DataFile("castellan.json"),
            TestWorlds.DataFile("villagers.json"), TestWorlds.DataFile("buildings.json"),
            TestWorlds.DataFile("recipes.json"), TestWorlds.DataFile("terrain.json")));
    }
}
