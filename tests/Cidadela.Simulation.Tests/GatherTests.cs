using Xunit;

namespace Cidadela.Simulation.Tests;

public class GatherTests
{
    private static SimWorld WorldWithTree() =>
        TestWorlds.Open(x: 3, z: 3, resources: """
            [{ "kind": "wood", "x": 5, "z": 3 }, { "kind": "stone", "x": 3, "z": 5 }]
            """);

    [Fact]
    public void GathersOneItemPerGatherTime()
    {
        SimWorld world = WorldWithTree();
        world.Enqueue(new GatherCommand(new GridPos(5, 3)));
        TestWorlds.Run(world, 20); // 1 comando + madeira leva 1 s = 20 ticks
        Assert.Equal(1, world.Castellan.Inventory.Count("wood"));
        Assert.Equal(29, world.ResourceAt(new GridPos(5, 3))!.Remaining);
    }

    [Fact]
    public void KeepsGatheringUntilStopped()
    {
        SimWorld world = WorldWithTree();
        world.Enqueue(new GatherCommand(new GridPos(5, 3)));
        TestWorlds.Run(world, 60);
        Assert.Equal(3, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void OutOfReachDoesNothing()
    {
        SimWorld world = TestWorlds.Open(x: 0, z: 0, resources: """[{ "kind": "wood", "x": 15, "z": 15 }]""");
        world.Enqueue(new GatherCommand(new GridPos(15, 15)));
        TestWorlds.Run(world, 40);
        Assert.Null(world.Castellan.GatherTarget);
        Assert.Equal(0, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void EmptyCellDoesNothing()
    {
        SimWorld world = WorldWithTree();
        world.Enqueue(new GatherCommand(new GridPos(8, 8)));
        TestWorlds.Run(world, 5);
        Assert.Null(world.Castellan.GatherTarget);
    }

    [Fact]
    public void WalkingStopsGathering()
    {
        SimWorld world = WorldWithTree();
        world.Enqueue(new GatherCommand(new GridPos(5, 3)));
        TestWorlds.Run(world, 10);
        TestWorlds.Move(world, 0f, -1f, ticks: 1);
        Assert.Null(world.Castellan.GatherTarget);
        TestWorlds.Move(world, 0f, 0f, ticks: 40);
        Assert.Equal(0, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void DepletedNodeStopsGatheringAndStopsBlocking()
    {
        SimWorld world = WorldWithTree();
        var stoneCell = new GridPos(3, 5);
        Assert.True(world.IsSolid(stoneCell));

        world.Enqueue(new GatherCommand(stoneCell));
        TestWorlds.Run(world, 100); // pedra: 2 itens × 30 ticks

        Assert.Equal(2, world.Castellan.Inventory.Count("stone"));
        Assert.Null(world.Castellan.GatherTarget);
        Assert.Null(world.ResourceAt(stoneCell));
        Assert.False(world.IsSolid(stoneCell));
    }

    [Fact]
    public void FacesTheResourceWhileGathering()
    {
        SimWorld world = WorldWithTree();
        world.Enqueue(new GatherCommand(new GridPos(5, 3)));
        TestWorlds.Run(world, 2);
        Assert.Equal(new System.Numerics.Vector2(1f, 0f), world.Castellan.Facing);
    }
}
