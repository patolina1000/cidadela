using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Carregadores: item do baú, da cabana ou da saída de máquina até a máquina que o aceita (dados de teste).</summary>
public class CarrierTests
{
    private static int Seconds(float s) => (int)(s * SimClock.TicksPerSecond);

    /// <summary>Posto de carregadores em (5, 5) com 2 carregadores ao lado, baú em (5, 10) e as construções dadas.</summary>
    private static SimWorld World(string buildings, string kind, int inChest)
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: $$"""
            [{ "kind": "carrier_post", "x": 5, "z": 5 }, { "kind": "chest", "x": 5, "z": 10 }{{buildings}}]
            """, villagers: """[{ "x": 4, "z": 5 }, { "x": 6, "z": 5 }]""");
        world.BuildingAt(new GridPos(5, 10))!.Storage!.Add(kind, inChest);
        return world;
    }

    [Fact]
    public void CarriersFillTheKilnFromTheChestAndStopAtItsRoom()
    {
        SimWorld world = World(""", { "kind": "kiln", "x": 10, "z": 10 }""", "wood", inChest: 40);
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
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: """
            [{ "kind": "carrier_post", "x": 5, "z": 5 }, { "kind": "kiln", "x": 10, "z": 10 },
             { "kind": "lumber_hut", "x": 5, "z": 10 }]
            """, villagers: """[{ "x": 4, "z": 5 }, { "x": 6, "z": 5 }]""");
        // Os dois aldeões vão para o posto de carregadores (construído primeiro); a cabana fica sem.
        world.BuildingAt(new GridPos(5, 10))!.Workplace!.Stored.Add("wood", 6);
        TestWorlds.Run(world, Seconds(40f));
        Assert.Equal(6, world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Count("wood"));
    }

    [Fact]
    public void CarriersBringLightItemsToo()
    {
        // D5 do Arthur (30/09): leve também vai nas costas (ineficiente, mas vai). A prensa guarda 2 hastes.
        SimWorld world = World(""", { "kind": "press", "x": 10, "z": 10 }""", "shaft", inChest: 5);
        TestWorlds.Run(world, Seconds(30f));
        Assert.Equal(2, world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Count("shaft"));
        Assert.Equal(3, world.BuildingAt(new GridPos(5, 10))!.Storage!.Count("shaft"));
    }

    [Fact]
    public void CarriersTakeFromTheOutputOfAMachine()
    {
        // Forno com hastes prontas na saída; a prensa pede hastes.
        SimWorld world = World(""", { "kind": "kiln", "x": 8, "z": 10 }, { "kind": "press", "x": 10, "z": 10 }""", "wood", inChest: 0);
        world.BuildingAt(new GridPos(8, 10))!.Machine!.Output.Add("shaft", 6);
        TestWorlds.Run(world, Seconds(20f));
        Assert.Equal(2, world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Count("shaft"));
        Assert.Equal(4, world.BuildingAt(new GridPos(8, 10))!.Machine!.Output.Count("shaft"));
    }

    [Fact]
    public void CarriersTakeTheHeavyLimitPerTrip()
    {
        SimWorld world = World(""", { "kind": "kiln", "x": 10, "z": 10 }""", "wood", inChest: 40);
        int most = 0;
        for (int i = 0; i < Seconds(20f); i++)
        {
            world.Tick();
            foreach (Villager v in world.Villagers)
                most = System.Math.Max(most, v.CarryingCount);
        }
        Assert.Equal(2, most); // pesado: 2 por viagem nos dados de teste (no jogo, 1)
    }

    [Fact]
    public void ALoadNobodyWantsGoesBackToTheChest()
    {
        // O forno encheu por outro caminho enquanto o carregador vinha: ele não fica preso com a carga na mão.
        SimWorld world = World(""", { "kind": "kiln", "x": 10, "z": 10 }""", "wood", inChest: 2);
        for (int i = 0; i < Seconds(10f) && world.Villagers.All(v => v.CarryingCount == 0); i++)
            world.Tick();
        world.BuildingAt(new GridPos(10, 10))!.Machine!.Input.Add("wood", 30); // 10 começam a queimar, 20 enchem a entrada
        TestWorlds.Run(world, Seconds(20f));
        Assert.All(world.Villagers, v => Assert.Equal(0, v.CarryingCount));
        Assert.Equal(2, world.BuildingAt(new GridPos(5, 10))!.Storage!.Count("wood"));
    }

    [Fact]
    public void MachinesOutsideTheRadiusAreIgnored()
    {
        SimWorld world = World(""", { "kind": "kiln", "x": 19, "z": 19 }""", "wood", inChest: 10);
        // Raio 12 do posto (5, 5): (19, 19) fica a 19,8 células.
        TestWorlds.Run(world, Seconds(30f));
        Assert.Equal(10, world.BuildingAt(new GridPos(5, 10))!.Storage!.Count("wood"));
    }

    [Fact]
    public void DeconstructingThePostGivesTheLoadToTheCastellan()
    {
        SimWorld world = World(""", { "kind": "kiln", "x": 10, "z": 10 }""", "wood", inChest: 40);
        int carried = 0;
        for (int i = 0; i < Seconds(8f) && carried == 0; i++)
        {
            world.Tick();
            carried = world.Villagers[0].CarryingCount + world.Villagers[1].CarryingCount;
        }
        Assert.True(carried > 0);
        // O Castelão em (1, 1) já alcança o posto (5, 5): alcance 10.
        world.Enqueue(new DeconstructCommand(new GridPos(5, 5)));
        world.Tick();
        Assert.All(world.Villagers, v => Assert.Null(v.Home));
        Assert.Equal(4 + carried, world.Castellan.Inventory.Count("wood")); // custo do posto + a carga
    }
}
