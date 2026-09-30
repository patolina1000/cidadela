using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Postos de máquina (dados de teste): só quem tem "operar" na ladainha ocupa; a máquina só anda com todos os postos
/// ocupados; desmontar trava a ladainha. Nenhuma construção chama ninguém.
/// </summary>
public class PostTests
{
    private static SimWorld Sawmill(string villagers)
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1,
            buildings: """[{ "kind": "crewed_mill", "x": 8, "z": 8, "direction": "east" }]""", villagers: villagers);
        world.BuildingAt(new GridPos(8, 8))!.Machine!.Input.Add("wood", 1);
        TestWorlds.OperateNearest(world);
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
        TestWorlds.Run(world, 2 * SimClock.TicksPerSecond + 5);
        Assert.Equal(2, world.BuildingAt(new GridPos(8, 8))!.Machine!.Output.Count("shaft"));
    }

    [Fact]
    public void OperatorsWalkToTheMachineAndStandOnDifferentSides()
    {
        SimWorld world = Sawmill("""[{ "x": 2, "z": 2 }, { "x": 14, "z": 14 }]""");
        Building sawmill = world.BuildingAt(new GridPos(8, 8))!;
        world.Tick();
        Assert.All(world.Villagers, v => Assert.Equal(VillagerTask.GoingToResource, v.Task));
        Assert.Equal(0, sawmill.CrewPresent);
        for (int i = 0; i < 30 * SimClock.TicksPerSecond && sawmill.CrewPresent < 2; i++)
            world.Tick();
        Assert.All(world.Villagers, v => Assert.Equal(VillagerTask.AtPost, v.Task));
        Assert.Equal(2, sawmill.CrewPresent);
        Assert.All(world.Villagers, v => Assert.Equal("saw", v.PostTool));
        GridPos[] cells = world.Villagers.Select(v => v.Cell).ToArray();
        Assert.NotEqual(cells[0], cells[1]);
        Assert.All(cells, c => Assert.True(System.Math.Abs(c.X - 8) + System.Math.Abs(c.Z - 8) == 1)); // de lado, encostado
    }

    [Fact]
    public void DeconstructingTheMachineStucksTheLitanyAndCallsNobody()
    {
        SimWorld world = TestWorlds.Open(x: 8, z: 6,
            buildings: """[{ "kind": "press", "x": 8, "z": 8 }]""", villagers: """[{ "x": 8, "z": 9 }]""");
        world.BuildingAt(new GridPos(8, 8))!.Machine!.Input.Add("shaft", 2);
        TestWorlds.OperateNearest(world);
        TestWorlds.Run(world, 2);
        Villager smith = world.Villagers[0];
        Assert.Equal(VillagerTask.AtPost, smith.Task);

        world.Castellan.Inventory.Add("wood", 8);
        world.Enqueue(new BuildCommand("crewed_mill", new GridPos(10, 8), Direction.East));
        world.Enqueue(new DeconstructCommand(new GridPos(8, 8)));
        TestWorlds.Run(world, 3);
        Assert.Null(smith.Home); // soltou o posto e ninguém o chamou para a serraria nova
        Assert.Equal(LitanyStuck.NoPlace, smith.Stuck);
        Assert.All(world.BuildingAt(new GridPos(10, 8))!.Crew, c => Assert.Null(c));
    }

    [Fact]
    public void MachineWithoutPostsRunsAlone()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: """[{ "kind": "kiln", "x": 8, "z": 8 }]""");
        Building kiln = world.BuildingAt(new GridPos(8, 8))!;
        Assert.True(kiln.CrewReady);
        kiln.Machine!.Input.Add("wood", 10);
        world.Tick();
        Assert.True(kiln.Machine.IsWorking);
    }
}
