using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class VillagerTests
{
    // Cabana de teste: raio 8, guarda até 3; aldeão: 5 células/s, 1 madeira por s, carrega 2.
    private static SimWorld World(string resources, string villagers = """[{ "x": 2, "z": 2 }]""",
        string buildings = """[{ "kind": "lumber_hut", "x": 4, "z": 4, "direction": "east" }]""") =>
        TestWorlds.Open(x: 1, z: 18, resources: resources, buildings: buildings, villagers: villagers);

    private static Villager First(SimWorld world) => world.Villagers[0];
    private static Workplace Hut(SimWorld world) => world.BuildingAt(new GridPos(4, 4))!.Workplace!;

    [Fact]
    public void ANewHutCallsTheNearestIdleVillager()
    {
        SimWorld world = World("[]", villagers: """[{ "x": 15, "z": 15 }, { "x": 3, "z": 3 }]""");
        Assert.Equal(world.Villagers[1], Hut(world).Worker);
        Assert.Equal(VillagerTask.Unemployed, world.Villagers[0].Task);
    }

    [Fact]
    public void GathersAndDeliversToTheHut()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        TestWorlds.Run(world, 200); // ida, 2 madeiras (40 ticks), volta
        Assert.True(Hut(world).Stored.Count("wood") >= 2);
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
        string resources = """
            [{ "kind": "wood", "x": 8, "z": 4 },
             { "kind": "stone", "x": 6, "z": 2 }, { "kind": "stone", "x": 6, "z": 3 }, { "kind": "stone", "x": 6, "z": 4 },
             { "kind": "stone", "x": 6, "z": 5 }, { "kind": "stone", "x": 6, "z": 6 }]
            """;
        SimWorld world = World(resources);
        TestWorlds.Run(world, 400);
        Assert.True(Hut(world).Stored.Count("wood") >= 2);
    }

    [Fact]
    public void GoesToTheNearestResourceInsideTheRadius()
    {
        SimWorld world = World("""
            [{ "kind": "wood", "x": 11, "z": 4 }, { "kind": "wood", "x": 5, "z": 7 }, { "kind": "wood", "x": 18, "z": 18 }]
            """);
        TestWorlds.Run(world, 5);
        Assert.Equal(new GridPos(5, 7), First(world).Target!.Cell);
    }

    [Fact]
    public void WaitsWhenThereIsNothingToGather()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 18, "z": 18 }]"""); // fora do raio 8
        TestWorlds.Run(world, 60);
        Assert.Equal(VillagerTask.Waiting, First(world).Task);
        Assert.Null(First(world).Target);
    }

    [Fact]
    public void StopsWhenTheHutIsFull()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        TestWorlds.Run(world, 1200);
        Assert.Equal(3, Hut(world).Stored.Count("wood"));
        Assert.Equal(VillagerTask.Waiting, First(world).Task);
    }

    [Fact]
    public void HutPushesOntoTheBeltInFront()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 4, "z": 7 }]""", buildings: """
            [{ "kind": "lumber_hut", "x": 4, "z": 4, "direction": "east" },
             { "kind": "belt", "x": 5, "z": 4, "direction": "east" }, { "kind": "chest", "x": 6, "z": 4 }]
            """);
        TestWorlds.Run(world, 600);
        Assert.True(world.BuildingAt(new GridPos(6, 4))!.Storage!.Count("wood") >= 2);
    }

    [Fact]
    public void DeconstructingTheHutFreesTheWorkerAndReturnsItems()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        TestWorlds.Run(world, 200);
        int stored = Hut(world).Stored.Count("wood");
        int carried = First(world).CarryingCount;

        world.Castellan.Inventory.Add("wood", 0);
        TestWorlds.Move(world, 1f, -1f, ticks: 40); // chega perto para ter alcance
        TestWorlds.Move(world, 0f, 0f, ticks: 1);
        int before = world.Castellan.Inventory.Count("wood");
        world.Enqueue(new DeconstructCommand(new GridPos(4, 4)));
        world.Tick();

        Assert.Null(world.BuildingAt(new GridPos(4, 4)));
        Assert.Equal(VillagerTask.Unemployed, First(world).Task);
        Assert.Equal(0, First(world).CarryingCount);
        Assert.True(world.Castellan.Inventory.Count("wood") >= before + 2 + stored);
        _ = carried;
    }

    [Fact]
    public void AFreedWorkerMovesToAnotherEmptyHut()
    {
        SimWorld world = World("[]", buildings: """
            [{ "kind": "lumber_hut", "x": 4, "z": 4 }, { "kind": "lumber_hut", "x": 8, "z": 8 }]
            """);
        Building second = world.BuildingAt(new GridPos(8, 8))!;
        Assert.Null(second.Workplace!.Worker); // só há 1 aldeão

        TestWorlds.Move(world, 1f, -1f, ticks: 40);
        TestWorlds.Move(world, 0f, 0f, ticks: 1);
        world.Enqueue(new DeconstructCommand(new GridPos(4, 4)));
        world.Tick();

        Assert.Equal(First(world), second.Workplace!.Worker);
        Assert.Same(second, First(world).Home);
    }
}
