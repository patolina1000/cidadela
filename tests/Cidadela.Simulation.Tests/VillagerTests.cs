using Xunit;
using static Cidadela.Simulation.Tests.TestWorlds;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Aldeão (docs/ladainhas.md): não faz nada sozinho; com a ladainha "colher tora perto do baú e pôr nele", colhe e entrega.
/// Dados de teste: 5 células/s, 1 madeira por s, carrega 2 pesados por ponto de Força.
/// </summary>
public class VillagerTests
{
    /// <summary>Baú em (4, 4); aldeão em (2, 2) com a ladainha de colher tora perto do baú (raio 8) e pôr nele.</summary>
    private static SimWorld World(string resources, bool withLitany = true)
    {
        SimWorld world = Open(x: 1, z: 18, resources: resources, buildings: """[{ "kind": "chest", "x": 4, "z": 4 }]""",
            villagers: """[{ "x": 2, "z": 2 }]""");
        if (withLitany)
            Teach(world, First(world), Litany(Gather("wood", 4, 4), Put("wood", 4, 4)));
        return world;
    }

    private static Villager First(SimWorld world) => world.Villagers[0];
    private static Inventory Chest(SimWorld world) => world.BuildingAt(new GridPos(4, 4))!.Storage!;

    [Fact]
    public void HutsAndPostsNeverCallAnyone()
    {
        SimWorld world = Open(x: 1, z: 18, buildings: """
            [{ "kind": "lumber_hut", "x": 4, "z": 4 }, { "kind": "press", "x": 8, "z": 8 }, { "kind": "carrier_post", "x": 12, "z": 4 }]
            """, villagers: """[{ "x": 5, "z": 5 }, { "x": 8, "z": 9 }]""");
        world.BuildingAt(new GridPos(4, 4))!.Workplace!.Stored.Add("wood", 3);
        Run(world, 10 * SimClock.TicksPerSecond);
        Assert.All(world.Villagers, v => Assert.Null(v.Home));
        Assert.Equal(new GridPos(5, 5), world.Villagers[0].Cell);
        Assert.Equal(new GridPos(8, 9), world.Villagers[1].Cell);
        Assert.All(world.Villagers, v => Assert.Equal(VillagerStatus.NoLitany, v.Status));
        Assert.Equal(3, world.BuildingAt(new GridPos(4, 4))!.Workplace!.Stored.Count("wood")); // a cabana não solta nada
    }

    [Fact]
    public void GathersAndDeliversToTheChest()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        Run(world, 200); // ida, 2 madeiras (40 ticks), volta
        Assert.True(Chest(world).Count("wood") >= 2);
        Assert.True(world.ResourceAt(new GridPos(7, 4))!.Remaining <= 28);
    }

    [Fact]
    public void CarriesAtMostTheCarryLimit()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        for (int i = 0; i < 300; i++)
        {
            world.Tick();
            Assert.True(First(world).CarryingCount <= 2);
        }
    }

    [Fact]
    public void WalksAroundObstaclesToReachTheResource()
    {
        // Árvore alvo em (8, 4) atrás de uma parede de pedras em x = 6 (z = 2..6).
        SimWorld world = World("""
            [{ "kind": "wood", "x": 8, "z": 4 },
             { "kind": "stone", "x": 6, "z": 2 }, { "kind": "stone", "x": 6, "z": 3 }, { "kind": "stone", "x": 6, "z": 4 },
             { "kind": "stone", "x": 6, "z": 5 }, { "kind": "stone", "x": 6, "z": 6 }]
            """);
        Run(world, 400);
        Assert.True(Chest(world).Count("wood") >= 2);
    }

    [Fact]
    public void GoesToTheNearestResourceInsideTheRadius()
    {
        SimWorld world = World("""
            [{ "kind": "wood", "x": 11, "z": 4 }, { "kind": "wood", "x": 5, "z": 7 }, { "kind": "wood", "x": 18, "z": 18 }]
            """);
        Run(world, 5);
        Assert.Equal(new GridPos(5, 7), First(world).Target!.Cell);
    }

    [Fact]
    public void NothingToGatherInsideTheRadiusStucksWithAReason()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 18, "z": 18 }]"""); // fora do raio 8
        Run(world, 60);
        Assert.Equal(LitanyStuck.NoResource, First(world).Stuck);
        Assert.Null(First(world).Target);
    }

    [Fact]
    public void WithoutALitanyNothingHappensEvenWithWorkAround()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""", withLitany: false);
        Run(world, 400);
        Assert.True(Chest(world).IsEmpty);
        Assert.Equal(new GridPos(2, 2), First(world).Cell);
    }

    [Fact]
    public void DeconstructingTheChestStucksThePut()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        Run(world, 60); // já colhendo
        Move(world, 1f, -1f, ticks: 40);
        Move(world, 0f, 0f, ticks: 1);
        world.Enqueue(new DeconstructCommand(new GridPos(4, 4)));
        Run(world, 200);
        Assert.Equal(LitanyStuck.NoPlace, First(world).Stuck);
    }
}
