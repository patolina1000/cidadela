using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Carregadores: bruto do baú ou da cabana até a máquina que o aceita.</summary>
public class CarrierTests
{
    private static int Seconds(float s) => (int)(s * SimClock.TicksPerSecond);

    /// <summary>Posto de carregadores em (5, 5) com 2 carregadores ao lado, baú em (5, 10) e as construções dadas.</summary>
    private static SimWorld World(string buildings, string kind, int inChest)
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), buildings: $$"""
            [{ "kind": "carrier_post", "x": 5, "z": 5 }, { "kind": "chest", "x": 5, "z": 10 }{{buildings}}]
            """, villagers: """[{ "x": 4, "z": 5 }, { "x": 6, "z": 5 }]""");
        world.BuildingAt(new GridPos(5, 10))!.Storage!.Add(kind, inChest);
        return world;
    }

    [Fact]
    public void CarriersFillTheSmelterFromTheChestAndStopAtItsRoom()
    {
        SimWorld world = World(""", { "kind": "smelter", "x": 10, "z": 10 }""", "iron", inChest: 10);
        Building smelter = world.BuildingAt(new GridPos(10, 10))!;
        TestWorlds.Run(world, Seconds(60f));
        // A fundição não tem fundidor (os dois aldeões são carregadores): 4 minérios na entrada (2 ciclos) e só.
        Assert.Equal(4, smelter.Machine!.Input.Count("iron"));
        Assert.Equal(6, world.BuildingAt(new GridPos(5, 10))!.Storage!.Count("iron"));
        Assert.All(world.Villagers, v => Assert.Equal(0, v.CarryingCount));
    }

    [Fact]
    public void CarriersTakeFromAHutToo()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), buildings: """
            [{ "kind": "carrier_post", "x": 5, "z": 5 }, { "kind": "smelter", "x": 10, "z": 10 },
             { "kind": "iron_hut", "x": 5, "z": 10 }]
            """, villagers: """[{ "x": 4, "z": 5 }, { "x": 6, "z": 5 }]""");
        // O primeiro aldeão vai para o posto de carregadores (construído primeiro), o segundo também; a cabana fica sem.
        world.BuildingAt(new GridPos(5, 10))!.Workplace!.Stored.Add("iron", 6);
        TestWorlds.Run(world, Seconds(40f));
        Assert.Equal(4, world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Count("iron"));
        Assert.Equal(2, world.BuildingAt(new GridPos(5, 10))!.Workplace!.Stored.Count("iron"));
    }

    [Fact]
    public void CarriersDoNotBringProcessedItems()
    {
        // A forja aceita lingote, mas lingote é processado: carregador não leva.
        SimWorld world = World(""", { "kind": "forge", "x": 10, "z": 10 }""", "ingot", inChest: 5);
        TestWorlds.Run(world, Seconds(30f));
        Assert.Equal(0, world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Count("ingot"));
        Assert.All(world.Villagers, v => Assert.Equal(VillagerStatus.NothingToHaul, v.Status));
    }

    [Fact]
    public void MachinesOutsideTheRadiusAreIgnored()
    {
        SimWorld world = World(""", { "kind": "smelter", "x": 19, "z": 19 }""", "iron", inChest: 10);
        // Raio 12 do posto (5, 5): (19, 19) fica a 19,8 células.
        TestWorlds.Run(world, Seconds(30f));
        Assert.Equal(10, world.BuildingAt(new GridPos(5, 10))!.Storage!.Count("iron"));
    }

    [Fact]
    public void DeconstructingThePostGivesTheLoadToTheCastellan()
    {
        SimWorld world = World(""", { "kind": "smelter", "x": 10, "z": 10 }""", "iron", inChest: 10);
        TestWorlds.Run(world, Seconds(8f));
        int carried = world.Villagers[0].CarryingCount + world.Villagers[1].CarryingCount;
        Assert.True(carried > 0);
        // O Castelão em (1, 1) já alcança o posto (5, 5): alcance 10.
        world.Enqueue(new DeconstructCommand(new GridPos(5, 5)));
        world.Tick();
        // Ninguém fica no posto desmontado (um deles é chamado para o posto vago da fundição).
        Assert.All(world.Villagers, v => Assert.NotEqual("carrier_post", v.Home?.Kind));
        Assert.Equal(4, world.Castellan.Inventory.Count("wood")); // custo do posto
        Assert.Equal(carried, world.Castellan.Inventory.Count("iron")); // a carga
    }
}
