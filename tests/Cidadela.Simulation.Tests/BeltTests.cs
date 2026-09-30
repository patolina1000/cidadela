using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class BeltTests
{
    // Esteira a 1,5 célula/s = 0,075 por tick.
    private const float Step = 1.5f / SimClock.TicksPerSecond;

    /// <summary>Castelão em (4, 4) com hastes (item leve: pesado não entra em esteira) e as construções dadas.</summary>
    private static SimWorld World(string buildings, int wood = 10)
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4, buildings: buildings);
        world.Castellan.Inventory.Add("shaft", wood);
        return world;
    }

    private static void Insert(SimWorld world, int x, int z)
    {
        world.Enqueue(new InsertItemCommand(new GridPos(x, z), "shaft"));
        world.Tick();
    }

    private static BeltLane Lane(SimWorld world, int x, int z) => world.BuildingAt(new GridPos(x, z))!.Belt!;

    [Fact]
    public void InsertedItemMovesAtBeltSpeed()
    {
        SimWorld world = World("""[{ "kind": "belt", "x": 6, "z": 4, "direction": "east" }]""");
        Insert(world, 6, 4); // entra e já anda 1 tick
        TestWorlds.Run(world, 9);
        Assert.Equal(10 * Step, Lane(world, 6, 4).Items[0].Progress, 3);
        Assert.Equal(9, world.Castellan.Inventory.Count("shaft"));
    }

    [Fact]
    public void StopsAtTheEndWhenNothingIsAhead()
    {
        SimWorld world = World("""[{ "kind": "belt", "x": 6, "z": 4, "direction": "east" }]""");
        Insert(world, 6, 4);
        TestWorlds.Run(world, 60);
        Assert.Single(Lane(world, 6, 4).Items);
        Assert.Equal(1f, Lane(world, 6, 4).Items[0].Progress);
    }

    [Fact]
    public void ItemsQueueWithSpacingAndABeltHoldsThree()
    {
        SimWorld world = World("""[{ "kind": "belt", "x": 6, "z": 4, "direction": "east" }]""");
        for (int i = 0; i < 5; i++)
        {
            Insert(world, 6, 4);
            TestWorlds.Run(world, 20);
        }
        BeltLane lane = Lane(world, 6, 4);
        Assert.Equal(3, lane.Items.Count);
        Assert.Equal(new[] { 1f, 0.5f, 0f }, lane.Items.Select(i => i.Progress).ToArray());
        Assert.Equal(7, world.Castellan.Inventory.Count("shaft")); // as 2 que não couberam ficaram
    }

    [Fact]
    public void PassesToTheNextBelt()
    {
        SimWorld world = World("""
            [{ "kind": "belt", "x": 6, "z": 4, "direction": "east" },
             { "kind": "belt", "x": 7, "z": 4, "direction": "east" }]
            """);
        Insert(world, 6, 4);
        TestWorlds.Run(world, 60);
        Assert.Empty(Lane(world, 6, 4).Items);
        Assert.Equal(1f, Lane(world, 7, 4).Items[0].Progress);
    }

    [Fact]
    public void TurnsACorner()
    {
        SimWorld world = World("""
            [{ "kind": "belt", "x": 6, "z": 4, "direction": "east" },
             { "kind": "belt", "x": 7, "z": 4, "direction": "south" }]
            """);
        Insert(world, 6, 4);
        TestWorlds.Run(world, 60);
        BeltItem item = Lane(world, 7, 4).Items[0];
        // Fim da esteira que desce: meia célula ao sul do centro de (7, 4).
        Assert.Equal(new System.Numerics.Vector2(7f, 4.5f), item.Position);
    }

    [Fact]
    public void HeadOnBeltDoesNotAccept()
    {
        SimWorld world = World("""
            [{ "kind": "belt", "x": 6, "z": 4, "direction": "east" },
             { "kind": "belt", "x": 7, "z": 4, "direction": "west" }]
            """);
        Insert(world, 6, 4);
        TestWorlds.Run(world, 60);
        Assert.Single(Lane(world, 6, 4).Items);
        Assert.Empty(Lane(world, 7, 4).Items);
    }

    [Fact]
    public void BeltDeliversIntoAChest()
    {
        SimWorld world = World("""
            [{ "kind": "belt",  "x": 6, "z": 4, "direction": "east" },
             { "kind": "chest", "x": 7, "z": 4 }]
            """);
        Insert(world, 6, 4);
        TestWorlds.Run(world, 60);
        Assert.Empty(Lane(world, 6, 4).Items);
        Assert.Equal(1, world.BuildingAt(new GridPos(7, 4))!.Storage!.Count("shaft"));
    }

    [Fact]
    public void InsertIntoChestAndTakeEverythingBack()
    {
        SimWorld world = World("""[{ "kind": "chest", "x": 6, "z": 4 }]""", wood: 3);
        Insert(world, 6, 4);
        Insert(world, 6, 4);
        Inventory chest = world.BuildingAt(new GridPos(6, 4))!.Storage!;
        Assert.Equal(2, chest.Count("shaft"));
        Assert.Equal(1, world.Castellan.Inventory.Count("shaft"));

        world.Enqueue(new TakeAllCommand(new GridPos(6, 4)));
        world.Tick();
        Assert.True(chest.IsEmpty);
        Assert.Equal(3, world.Castellan.Inventory.Count("shaft"));
    }

    [Fact]
    public void CannotInsertWithoutTheItemOrOutOfReach()
    {
        SimWorld world = World("""
            [{ "kind": "belt", "x": 6, "z": 4, "direction": "east" },
             { "kind": "belt", "x": 18, "z": 18, "direction": "east" }]
            """, wood: 0);
        Insert(world, 6, 4);
        Assert.Empty(Lane(world, 6, 4).Items);

        world.Castellan.Inventory.Add("shaft", 1);
        Insert(world, 18, 18);
        Assert.Empty(Lane(world, 18, 18).Items);
        Assert.Equal(1, world.Castellan.Inventory.Count("shaft"));
    }

    [Fact]
    public void DeconstructingReturnsWhatWasOnOrInside()
    {
        SimWorld world = World("""
            [{ "kind": "belt",  "x": 6, "z": 4, "direction": "east" },
             { "kind": "chest", "x": 6, "z": 5 }]
            """, wood: 3);
        Insert(world, 6, 4);
        Insert(world, 6, 5);
        Insert(world, 6, 5);
        Assert.Equal(0, world.Castellan.Inventory.Count("shaft"));

        world.Enqueue(new DeconstructCommand(new GridPos(6, 4)));
        world.Enqueue(new DeconstructCommand(new GridPos(6, 5)));
        world.Tick();

        // 1 no cinto + 2 no baú; os custos (1 + 4) voltam em madeira.
        Assert.Equal(3, world.Castellan.Inventory.Count("shaft"));
        Assert.Equal(5, world.Castellan.Inventory.Count("wood"));
        Assert.Empty(world.BeltItems);
    }

    [Fact]
    public void PreviousPositionLetsTheViewInterpolate()
    {
        SimWorld world = World("""[{ "kind": "belt", "x": 6, "z": 4, "direction": "east" }]""");
        Insert(world, 6, 4);
        world.Tick();
        BeltItem item = world.BeltItems.Single();
        Assert.Equal(Step, item.Position.X - item.PreviousPosition.X, 3);
    }
}
