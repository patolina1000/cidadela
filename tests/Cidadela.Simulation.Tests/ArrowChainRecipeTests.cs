using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Máquinas e receitas da linha da flecha com os números de data/ (docs/cadeia_flecha.md).</summary>
public class ArrowChainRecipeTests
{
    private static int Ticks(float seconds) => (int)(seconds * SimClock.TicksPerSecond);

    /// <summary>A máquina em (8, 8) com dois aldeões já encostados (8, 7) e (8, 9): os postos se ocupam no 1º tick.</summary>
    private static (SimWorld World, Building Machine) Machine(string kind)
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(),
            buildings: $$"""[{ "kind": "{{kind}}", "x": 8, "z": 8, "direction": "east" }]""",
            villagers: """[{ "x": 8, "z": 7 }, { "x": 8, "z": 9 }]""");
        TestWorlds.Run(world, 2);
        return (world, world.BuildingAt(new GridPos(8, 8))!);
    }

    [Theory]
    [InlineData("sawmill", "wood", 1, "shaft", 4, 8f)]
    [InlineData("charcoal_kiln", "wood", 10, "charcoal", 20, 120f)]
    [InlineData("anvil", "ingot", 1, "point", 3, 15f)]
    public void OneInputMachinesFollowTheData(string kind, string input, int inputs, string output, int outputs, float seconds)
    {
        (SimWorld world, Building machine) = Machine(kind);
        machine.Machine!.Input.Add(input, inputs);
        TestWorlds.Run(world, Ticks(seconds) - 1);
        Assert.Equal(0, machine.Machine.Output.Count(output));
        TestWorlds.Run(world, 2);
        Assert.Equal(outputs, machine.Machine.Output.Count(output));
    }

    [Fact]
    public void SmelterNeedsOreAndCharcoal()
    {
        (SimWorld world, Building smelter) = Machine("smelter");
        smelter.Machine!.Input.Add("iron", 1);
        TestWorlds.Run(world, Ticks(20f));
        Assert.Equal(0, smelter.Machine.Output.Count("ingot"));
        smelter.Machine.Input.Add("charcoal", 1);
        TestWorlds.Run(world, Ticks(15f) + 1);
        Assert.Equal(1, smelter.Machine.Output.Count("ingot"));
    }

    [Fact]
    public void CoopMakesFeathersFromNothing()
    {
        (SimWorld world, Building coop) = Machine("coop");
        TestWorlds.Run(world, Ticks(30f) + 1);
        Assert.Equal(3, coop.Machine!.Output.Count("feather"));
    }

    [Fact]
    public void FletchingTableMakesTwoArrows()
    {
        (SimWorld world, Building table) = Machine("fletching_table");
        table.Machine!.Input.Add("shaft", 1);
        table.Machine.Input.Add("point", 1);
        table.Machine.Input.Add("feather", 1);
        TestWorlds.Run(world, Ticks(12f));
        Assert.Equal(0, table.Machine.Output.Count("arrow"));
        table.Machine.Input.Add("feather", 1);
        TestWorlds.Run(world, Ticks(10f) + 1);
        Assert.Equal(2, table.Machine.Output.Count("arrow"));
    }

    [Fact]
    public void ArsenalStoresArrowsFromABelt()
    {
        SimWorld world = TestWorlds.Open(x: 5, z: 5, data: TestWorlds.RealData(), buildings: """
            [{ "kind": "belt", "x": 6, "z": 5, "direction": "east" }, { "kind": "arsenal", "x": 7, "z": 5 },
             { "kind": "crank", "x": 6, "z": 6, "direction": "north" }]
            """, villagers: """[{ "x": 6, "z": 7 }]""");
        TestWorlds.Run(world, 2); // o girador chega à manivela
        world.Castellan.Inventory.Add("arrow", 2);
        world.Enqueue(new InsertItemCommand(new GridPos(6, 5), "arrow"));
        TestWorlds.Run(world, Ticks(2f));
        Assert.Equal(1, world.BuildingAt(new GridPos(7, 5))!.Storage!.Count("arrow"));
    }
}
