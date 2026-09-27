using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Alimentador do palco da Biografia: itens nascem na entrada de uma esteira sem o Castelão.</summary>
public class SpawnItemTests
{
    private static SimWorld World() => TestWorlds.Open(x: 10, z: 10,
        buildings: """[{ "kind": "belt", "x": 2, "z": 2, "direction": "east" }, { "kind": "chest", "x": 5, "z": 5 }]""");

    [Fact]
    public void SpawnsOnABeltFarFromTheCastellan()
    {
        SimWorld world = World();
        world.Enqueue(new SpawnItemCommand(new GridPos(2, 2), "wood"));
        world.Tick();
        Assert.Single(world.BeltItems);
        Assert.Equal("wood", world.BeltItems.First().Kind);
    }

    [Fact]
    public void DoesNothingOnAChestOrEmptyCell()
    {
        SimWorld world = World();
        world.Enqueue(new SpawnItemCommand(new GridPos(5, 5), "wood"));
        world.Enqueue(new SpawnItemCommand(new GridPos(7, 7), "wood"));
        world.Tick();
        Assert.Empty(world.BeltItems);
        Assert.Equal(0, world.BuildingAt(new GridPos(5, 5))!.Storage!.Count("wood"));
    }

    [Fact]
    public void RespectsTheSpacingAtTheEntry()
    {
        SimWorld world = World();
        world.Enqueue(new SpawnItemCommand(new GridPos(2, 2), "wood"));
        world.Enqueue(new SpawnItemCommand(new GridPos(2, 2), "wood")); // mesmo tick: sem espaço ainda
        world.Tick();
        Assert.Single(world.BeltItems);
    }
}
