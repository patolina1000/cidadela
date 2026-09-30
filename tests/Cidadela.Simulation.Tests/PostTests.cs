using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Postos de máquina (docs/cadeia_flecha.md): aldeão ocupa, máquina só anda com todos, desmontar libera.</summary>
public class PostTests
{
    private static SimWorld Sawmill(string villagers)
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(),
            buildings: """[{ "kind": "sawmill", "x": 8, "z": 8, "direction": "east" }]""", villagers: villagers);
        world.BuildingAt(new GridPos(8, 8))!.Machine!.Input.Add("wood", 1);
        return world;
    }

    [Fact]
    public void SawmillWithOneSawyerDoesNotRun()
    {
        SimWorld world = Sawmill("""[{ "x": 8, "z": 7 }]""");
        TestWorlds.Run(world, 200);
        MachineState machine = world.BuildingAt(new GridPos(8, 8))!.Machine!;
        Assert.Equal(0, machine.Output.Count("shaft"));
        Assert.Equal(MachineWait.PostsEmpty, machine.Waiting);
    }

    [Fact]
    public void SawmillRunsWithBothSawyers()
    {
        SimWorld world = Sawmill("""[{ "x": 8, "z": 7 }, { "x": 8, "z": 9 }]""");
        TestWorlds.Run(world, 8 * SimClock.TicksPerSecond + 2);
        Assert.Equal(4, world.BuildingAt(new GridPos(8, 8))!.Machine!.Output.Count("shaft"));
    }

    [Fact]
    public void CalledVillagersWalkToTheMachineAndStandOnDifferentSides()
    {
        SimWorld world = Sawmill("""[{ "x": 2, "z": 2 }, { "x": 14, "z": 14 }]""");
        Building sawmill = world.BuildingAt(new GridPos(8, 8))!;
        world.Tick();
        Assert.All(world.Villagers, v => Assert.Equal(VillagerTask.GoingToPost, v.Task));
        Assert.Equal(0, sawmill.CrewPresent);
        TestWorlds.Run(world, 30 * SimClock.TicksPerSecond);
        Assert.Equal(2, sawmill.CrewPresent);
        Assert.All(world.Villagers, v => Assert.Equal("saw", v.PostTool));
        GridPos[] cells = world.Villagers.Select(v => v.Cell).ToArray();
        Assert.NotEqual(cells[0], cells[1]);
        Assert.All(cells, c => Assert.True(System.Math.Abs(c.X - 8) + System.Math.Abs(c.Z - 8) == 1)); // de lado, encostado
    }

    [Fact]
    public void DeconstructingFreesTheCrewForAnotherPost()
    {
        SimWorld world = TestWorlds.Open(x: 8, z: 6, data: TestWorlds.RealData(),
            buildings: """[{ "kind": "anvil", "x": 8, "z": 8 }]""", villagers: """[{ "x": 8, "z": 9 }]""");
        TestWorlds.Run(world, 2);
        Villager smith = world.Villagers[0];
        Assert.Equal(VillagerTask.AtPost, smith.Task);

        world.Castellan.Inventory.Add("wood", 10);
        world.Enqueue(new BuildCommand("coop", new GridPos(10, 8), Direction.East));
        world.Tick();
        Assert.Equal(VillagerTask.AtPost, smith.Task); // o posto dele não muda por causa de outra máquina

        world.Enqueue(new DeconstructCommand(new GridPos(8, 8)));
        world.Tick();
        Assert.Same(world.BuildingAt(new GridPos(10, 8)), smith.Home); // foi chamado para o galinheiro vago
        TestWorlds.Run(world, 10 * SimClock.TicksPerSecond);
        Assert.Equal("basket", smith.PostTool);
    }

    [Fact]
    public void MachineWithoutPostsRunsAlone()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(),
            buildings: """[{ "kind": "charcoal_kiln", "x": 8, "z": 8 }]""");
        Building kiln = world.BuildingAt(new GridPos(8, 8))!;
        Assert.True(kiln.CrewReady);
        kiln.Machine!.Input.Add("wood", 10);
        world.Tick();
        Assert.True(kiln.Machine.IsWorking);
    }
}
