using Xunit;

namespace Cidadela.Simulation.Tests;

public class BuildTests
{
    private static SimWorld WorldWithWood(int wood)
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4);
        world.Castellan.Inventory.Add("wood", wood);
        return world;
    }

    private static void Build(SimWorld world, string kind, int x, int z, Direction dir = Direction.North)
    {
        world.Enqueue(new BuildCommand(kind, new GridPos(x, z), dir));
        world.Tick();
    }

    [Fact]
    public void BuildingSpendsTheCost()
    {
        SimWorld world = WorldWithWood(5);
        Build(world, "chest", 6, 4);
        Assert.Equal("chest", world.BuildingAt(new GridPos(6, 4))?.Kind);
        Assert.Equal(1, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void WithoutItemsNothingIsBuilt()
    {
        SimWorld world = WorldWithWood(3);
        Assert.Equal(BuildCheck.NotEnoughItems, world.CanBuild(world.Data.Building("chest"), new GridPos(6, 4)));
        Build(world, "chest", 6, 4);
        Assert.Null(world.BuildingAt(new GridPos(6, 4)));
        Assert.Equal(3, world.Castellan.Inventory.Count("wood"));
    }

    [Fact]
    public void OutOfReachNothingIsBuilt()
    {
        SimWorld world = WorldWithWood(10);
        Assert.Equal(BuildCheck.OutOfReach, world.CanBuild(world.Data.Building("belt"), new GridPos(18, 18)));
        Build(world, "belt", 18, 18);
        Assert.Null(world.BuildingAt(new GridPos(18, 18)));
    }

    [Fact]
    public void CannotBuildOnAnOccupiedCell()
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4, resources: """[{ "kind": "wood", "x": 6, "z": 4 }]""");
        world.Castellan.Inventory.Add("wood", 10);
        Assert.Equal(BuildCheck.Occupied, world.CanBuild(world.Data.Building("belt"), new GridPos(6, 4)));

        Build(world, "belt", 7, 4);
        Assert.Equal(BuildCheck.Occupied, world.CanBuild(world.Data.Building("chest"), new GridPos(7, 4)));
    }

    [Fact]
    public void SolidBuildingCannotGoOnTopOfTheCastellan()
    {
        SimWorld world = WorldWithWood(10);
        var underFeet = new GridPos(4, 4);
        Assert.Equal(BuildCheck.Occupied, world.CanBuild(world.Data.Building("chest"), underFeet));
        Assert.Equal(BuildCheck.Ok, world.CanBuild(world.Data.Building("belt"), underFeet));
    }

    [Fact]
    public void BeltsCanBeWalkedOverButChestsBlock()
    {
        SimWorld world = WorldWithWood(10);
        Build(world, "belt", 6, 4);
        Assert.False(world.IsSolid(new GridPos(6, 4)));
        Build(world, "chest", 6, 5);
        Assert.True(world.IsSolid(new GridPos(6, 5)));

        TestWorlds.Move(world, 1f, 0f, ticks: 20); // atravessa a esteira
        Assert.True(world.Castellan.Position.X > 7f);
    }

    [Fact]
    public void KeepsTheChosenDirection()
    {
        SimWorld world = WorldWithWood(1);
        Build(world, "belt", 5, 4, Direction.East);
        Assert.Equal(Direction.East, world.BuildingAt(new GridPos(5, 4))!.Direction);
    }

    [Fact]
    public void DeconstructingGivesTheCostBack()
    {
        SimWorld world = WorldWithWood(4);
        Build(world, "chest", 6, 4);
        Assert.Equal(0, world.Castellan.Inventory.Count("wood"));

        int version = world.BuildingsVersion;
        world.Enqueue(new DeconstructCommand(new GridPos(6, 4)));
        world.Tick();

        Assert.Null(world.BuildingAt(new GridPos(6, 4)));
        Assert.Equal(4, world.Castellan.Inventory.Count("wood"));
        Assert.NotEqual(version, world.BuildingsVersion);
        Assert.False(world.IsSolid(new GridPos(6, 4)));
    }

    [Fact]
    public void CannotDeconstructOutOfReach()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: """[{ "kind": "chest", "x": 18, "z": 18 }]""");
        world.Enqueue(new DeconstructCommand(new GridPos(18, 18)));
        world.Tick();
        Assert.NotNull(world.BuildingAt(new GridPos(18, 18)));
    }

    [Fact]
    public void RotatesClockwise()
    {
        Assert.Equal(Direction.East, Direction.North.RotatedClockwise());
        Assert.Equal(Direction.North, Direction.West.RotatedClockwise());
    }
}
