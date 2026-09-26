using Xunit;

namespace Cidadela.Simulation.Tests;

public class GatherTests
{
    // Castelão em (4, 4), árvore encostada a leste e pedra encostada ao sul.
    private static readonly GridPos Tree = new(5, 4);
    private static readonly GridPos Stone = new(4, 5);

    private static SimWorld WorldNextToTree() =>
        TestWorlds.Open(x: 4, z: 4, resources: """
            [{ "kind": "wood", "x": 5, "z": 4 }, { "kind": "stone", "x": 4, "z": 5 }]
            """);

    [Fact]
    public void GathersOneItemPerGatherTime()
    {
        SimWorld world = WorldNextToTree();
        world.Enqueue(new GatherCommand(Tree));
        TestWorlds.Run(world, 20); // 1 comando + madeira leva 1 s = 20 ticks
        Assert.Equal(1, world.Castellan.Inventory.Count("wood"));
        Assert.Equal(29, world.ResourceAt(Tree)!.Remaining);
    }

    [Fact]
    public void KeepsGatheringUntilStopped()
    {
        SimWorld world = WorldNextToTree();
        world.Enqueue(new GatherCommand(Tree));
        TestWorlds.Run(world, 60);
        Assert.Equal(3, world.Castellan.Inventory.Count("wood"));
    }

    [Theory]
    [InlineData(5, 4)] // de lado
    [InlineData(5, 5)] // na diagonal
    public void CanGatherWhenTouching(int x, int z)
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4);
        Assert.True(world.Castellan.CanGather(new GridPos(x, z)));
    }

    [Fact]
    public void TooFarToGatherEvenInsideBuildReach()
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4, resources: """[{ "kind": "wood", "x": 6, "z": 4 }]""");
        var tree = new GridPos(6, 4);
        Assert.True(world.Castellan.CanReach(tree));
        Assert.False(world.Castellan.CanGather(tree));

        world.Enqueue(new GatherCommand(tree));
        TestWorlds.Run(world, 40);
        Assert.Null(world.Castellan.GatherTarget);
        Assert.Equal(0, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void WalkingUpToTheTreeThenGatheringWorks()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 4, resources: """[{ "kind": "wood", "x": 6, "z": 4 }]""");
        TestWorlds.Move(world, 1f, 0f, ticks: 40); // anda até encostar
        TestWorlds.Move(world, 0f, 0f, ticks: 1);
        world.Enqueue(new GatherCommand(new GridPos(6, 4)));
        TestWorlds.Run(world, 21);
        Assert.Equal(1, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void EmptyCellDoesNothing()
    {
        SimWorld world = WorldNextToTree();
        world.Enqueue(new GatherCommand(new GridPos(3, 4)));
        TestWorlds.Run(world, 5);
        Assert.Null(world.Castellan.GatherTarget);
    }

    [Fact]
    public void WalkingStopsGathering()
    {
        SimWorld world = WorldNextToTree();
        world.Enqueue(new GatherCommand(Tree));
        TestWorlds.Run(world, 10);
        TestWorlds.Move(world, 0f, -1f, ticks: 1);
        Assert.Null(world.Castellan.GatherTarget);
        TestWorlds.Move(world, 0f, 0f, ticks: 40);
        Assert.Equal(0, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void DepletedNodeStopsGatheringAndStopsBlocking()
    {
        SimWorld world = WorldNextToTree();
        Assert.True(world.IsSolid(Stone));

        world.Enqueue(new GatherCommand(Stone));
        TestWorlds.Run(world, 100); // pedra: 2 itens × 30 ticks

        Assert.Equal(2, world.Castellan.Inventory.Count("stone"));
        Assert.Null(world.Castellan.GatherTarget);
        Assert.Null(world.ResourceAt(Stone));
        Assert.False(world.IsSolid(Stone));
    }

    [Fact]
    public void FacesTheResourceWhileGathering()
    {
        SimWorld world = WorldNextToTree();
        world.Enqueue(new GatherCommand(Tree));
        TestWorlds.Run(world, 2);
        Assert.Equal(new System.Numerics.Vector2(1f, 0f), world.Castellan.Facing);
    }
}
