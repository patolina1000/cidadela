using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Carregadores (docs/cadeia_flecha.md): bruto do baú ou da cabana até a máquina que o aceita.</summary>
public class CarrierTests
{
    private static int Seconds(float s) => (int)(s * SimClock.TicksPerSecond);

    /// <summary>Posto de carregadores em (5, 5) com 2 carregadores ao lado, baú em (5, 10) e as construções dadas.</summary>
    private static SimWorld World(string buildings, int woodInChest)
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), buildings: $$"""
            [{ "kind": "carrier_post", "x": 5, "z": 5 }, { "kind": "chest", "x": 5, "z": 10 }{{buildings}}]
            """, villagers: """[{ "x": 4, "z": 5 }, { "x": 6, "z": 5 }]""");
        world.BuildingAt(new GridPos(5, 10))!.Storage!.Add("wood", woodInChest);
        return world;
    }

    [Fact]
    public void CarriersFillTheKilnFromTheChestAndStopAtItsRoom()
    {
        SimWorld world = World(""", { "kind": "charcoal_kiln", "x": 10, "z": 10 }""", woodInChest: 40);
        Building kiln = world.BuildingAt(new GridPos(10, 10))!;
        TestWorlds.Run(world, Seconds(60f));
        // 10 toras já queimando + 20 na entrada (2 ciclos): nada a mais foi tirado do baú.
        Assert.True(kiln.Machine!.IsWorking);
        Assert.Equal(20, kiln.Machine.Input.Count("wood"));
        Assert.Equal(10, world.BuildingAt(new GridPos(5, 10))!.Storage!.Count("wood"));
        Assert.All(world.Villagers, v => Assert.Equal(0, v.CarryingCount));
    }

    [Fact]
    public void CarriersTakeFromAHutToo()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), buildings: """
            [{ "kind": "carrier_post", "x": 5, "z": 5 }, { "kind": "charcoal_kiln", "x": 10, "z": 10 },
             { "kind": "lumber_hut", "x": 5, "z": 10 }]
            """, villagers: """[{ "x": 4, "z": 5 }, { "x": 6, "z": 5 }]""");
        // O primeiro aldeão vai para o posto de carregadores (construído primeiro), o segundo também; a cabana fica sem.
        world.BuildingAt(new GridPos(5, 10))!.Workplace!.Stored.Add("wood", 6);
        TestWorlds.Run(world, Seconds(40f));
        Assert.Equal(6, world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Count("wood"));
    }

    [Fact]
    public void CarriersDoNotBringProcessedItems()
    {
        SimWorld world = World(""", { "kind": "anvil", "x": 10, "z": 10 }""", woodInChest: 0);
        world.BuildingAt(new GridPos(5, 10))!.Storage!.Add("ingot", 5);
        TestWorlds.Run(world, Seconds(30f));
        Assert.Equal(0, world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Count("ingot"));
        Assert.All(world.Villagers, v => Assert.Equal(VillagerStatus.NothingToHaul, v.Status));
    }

    [Fact]
    public void MachinesOutsideTheRadiusAreIgnored()
    {
        SimWorld world = World(""", { "kind": "charcoal_kiln", "x": 19, "z": 19 }""", woodInChest: 10);
        // Raio 12 do posto (5, 5): (19, 19) fica a 19,8 células.
        TestWorlds.Run(world, Seconds(30f));
        Assert.Equal(10, world.BuildingAt(new GridPos(5, 10))!.Storage!.Count("wood"));
    }

    [Fact]
    public void DeconstructingThePostGivesTheLoadToTheCastellan()
    {
        SimWorld world = World(""", { "kind": "charcoal_kiln", "x": 10, "z": 10 }""", woodInChest: 40);
        TestWorlds.Run(world, Seconds(8f));
        int carried = world.Villagers[0].CarryingCount + world.Villagers[1].CarryingCount;
        Assert.True(carried > 0);
        // O Castelão em (1, 1) já alcança o posto (5, 5): alcance 10.
        world.Enqueue(new DeconstructCommand(new GridPos(5, 5)));
        world.Tick();
        Assert.All(world.Villagers, v => Assert.Null(v.Home));
        Assert.Equal(4 + carried, world.Castellan.Inventory.Count("wood")); // custo do posto + a carga
    }
}
