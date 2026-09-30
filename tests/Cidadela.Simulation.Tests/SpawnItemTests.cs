using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Alimentador da vitrine da Biografia: põe o item direto na máquina (ou no baú), sem o Castelão.</summary>
public class SpawnItemTests
{
    private static SimWorld World() => TestWorlds.Open(x: 10, z: 10,
        buildings: """[{ "kind": "press", "x": 2, "z": 2 }, { "kind": "chest", "x": 5, "z": 5 }]""");

    [Fact]
    public void PutsTheItemIntoTheMachineFarFromTheCastellan()
    {
        SimWorld world = World();
        world.Enqueue(new SpawnItemCommand(new GridPos(2, 2), "shaft"));
        world.Tick();
        Assert.Equal(1, world.BuildingAt(new GridPos(2, 2))!.Machine!.Input.Count("shaft"));
    }

    [Fact]
    public void RespectsWhatTheMachineAccepts()
    {
        SimWorld world = World();
        for (int i = 0; i < 5; i++)
            world.Enqueue(new SpawnItemCommand(new GridPos(2, 2), "shaft"));
        world.Enqueue(new SpawnItemCommand(new GridPos(2, 2), "wood")); // a prensa não usa madeira
        world.Tick();
        Assert.Equal(2, world.BuildingAt(new GridPos(2, 2))!.Machine!.Input.Count("shaft")); // 2 ciclos
        Assert.Equal(0, world.BuildingAt(new GridPos(2, 2))!.Machine!.Input.Count("wood"));
    }

    [Fact]
    public void FillsAChestAndIgnoresAnEmptyCell()
    {
        SimWorld world = World();
        world.Enqueue(new SpawnItemCommand(new GridPos(5, 5), "wood"));
        world.Enqueue(new SpawnItemCommand(new GridPos(7, 7), "wood"));
        world.Tick();
        Assert.Equal(1, world.BuildingAt(new GridPos(5, 5))!.Storage!.Count("wood"));
    }
}
