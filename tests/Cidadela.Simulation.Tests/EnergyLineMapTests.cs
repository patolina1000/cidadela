using System.Linq;
using Xunit;
using Xunit.Abstractions;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Teste A (data/maps/linha_energia.json): a linha inteira montada, no layout estilo Factorio, anda sozinha e sobra mana. Teste B (data/maps/linha_energia_zero.json): nada construído, zero aldeões.
/// </summary>
public class EnergyLineMapTests
{
    private readonly ITestOutputHelper _output;

    public EnergyLineMapTests(ITestOutputHelper output) => _output = output;

    private static SimWorld Load() => MapLoader.Parse(TestWorlds.DataFile("maps/linha_energia.json"), TestWorlds.RealData());

    [Fact]
    public void EveryPostIsTakenAndEverythingIsPowered()
    {
        SimWorld world = Load();
        TestWorlds.Run(world, 5 * SimClock.TicksPerSecond);
        Assert.Single(world.ManaNetworks);
        foreach (Building b in world.Buildings.Where(b => b.Type.Mana is not null))
            Assert.NotNull(b.Network);
        foreach (Building b in world.Buildings.Where(b => b.Type.Posts is not null))
            Assert.True(b.CrewReady, $"{b.Kind} sem operador");
        Assert.Equal(4, world.Villagers.Count(v => v.Home is not null));
    }

    [Fact]
    public void TheLineRunsAloneAndTheSurplusReachesTheMotherCrystal()
    {
        SimWorld world = Load();
        Building reliquary = world.Buildings.Single(b => b.Kind == "reliquary");
        Building purifier = world.Buildings.Single(b => b.Kind == "purifier");
        Building mine = world.Buildings.Single(b => b.Kind == "crystal_mine");
        Building well = world.Buildings.Single(b => b.Kind == "well");
        Villager carrier = world.Villagers.Single(v => v.Home?.Kind == "carrier_post");
        int minutes = 10;
        for (int minute = 1; minute <= minutes; minute++)
        {
            float supply = 0f, demand = 0f;
            for (int i = 0; i < 60 * SimClock.TicksPerSecond; i++)
            {
                world.Tick();
                ManaNetwork n = world.ManaNetworks.Single();
                supply += n.Supply;
                demand += System.MathF.Min(n.Demand, n.Supply);
            }
            int ticks = 60 * SimClock.TicksPerSecond;
            _output.WriteLine($"min {minute}: gera {supply / ticks:0.00}/s, consome {demand / ticks:0.00}/s, " +
                $"sobra {(supply - demand) / ticks:0.00}/s; Relicário com {reliquary.Machine!.Input.Count("pure_shard")} puros; " +
                $"Purificador: {EnergyStates(purifier)} (entrada {Contents(purifier.Machine!.Input)}; saída {Contents(purifier.Machine.Output)}); " +
                $"Mina: {EnergyStates(mine)} {Contents(mine.Machine!.Output)}; Poço: {EnergyStates(well)} {Contents(well.Machine!.Output)}; " +
                $"carregador: {carrier.Status}; baú de sobras: {Contents(world.Buildings.Single(b => b.Kind == "chest").Storage!)}");
        }
        // A linha se sustenta: o Relicário nunca apagou de vez e sobra mana.
        Assert.True(reliquary.Machine!.IsWorking || reliquary.Machine.Input.Count("pure_shard") > 0, "o Relicário apagou");
        Assert.True(world.ManaNetworks.Single().Supply > 9f, "a rede ficou sem geração");
    }

    [Fact]
    public void NoBeltPointsIntoAMachine()
    {
        // Layout estilo Factorio (orientação do Arthur, 30/09): a esteira corre ao lado; só mariposa entra e sai.
        SimWorld world = Load();
        foreach (Building belt in world.Buildings.Where(b => b.Belt is not null))
            Assert.Null(world.BuildingAt(belt.Cell.Step(belt.Direction))?.Machine);
        foreach (Building machine in world.Buildings.Where(b => b.Machine is not null && b.Kind is not ("crystal_mine" or "mother_crystal")))
            Assert.Contains(world.Buildings, m => m.Moth is not null &&
                (m.Cell.Step(m.Direction) == machine.Cell || m.Cell.Step(m.Direction.Opposite()) == machine.Cell));
    }

    [Fact]
    public void ARealBeltPointingIntoARealMachineDeliversNothing()
    {
        SimWorld world = MapLoader.Parse("""
            { "width": 12, "height": 12, "castellan": { "x": 2, "z": 5 },
              "buildings": [{ "kind": "belt", "x": 4, "z": 5, "direction": "east" }, { "kind": "reliquary", "x": 5, "z": 5 }] }
            """, TestWorlds.RealData());
        world.Castellan.Inventory.Add("pure_shard", 3);
        for (int i = 0; i < 3; i++)
        {
            world.Enqueue(new InsertItemCommand(new GridPos(4, 5), "pure_shard"));
            TestWorlds.Run(world, SimClock.TicksPerSecond);
        }
        TestWorlds.Run(world, 10 * SimClock.TicksPerSecond);
        Assert.Equal(0, world.BuildingAt(new GridPos(5, 5))!.Machine!.Input.Count("pure_shard"));
        Assert.False(world.BuildingAt(new GridPos(5, 5))!.Machine!.IsWorking);
    }

    [Fact]
    public void TestBStartsWithNothingBuiltAndZeroVillagers()
    {
        SimWorld world = MapLoader.Parse(TestWorlds.DataFile("maps/linha_energia_zero.json"), TestWorlds.RealData());
        Assert.Empty(world.Villagers);
        Assert.Equal("mother_crystal", world.Buildings.Single().Kind);
        Assert.True(world.Castellan.Inventory.IsEmpty);
        foreach (string kind in new[] { "wood", "stone", "rotten_shard" })
            Assert.Contains(world.Resources, r => r.Kind == kind);
        Assert.False(world.IsSolid(new GridPos((int)world.Castellan.Position.X, (int)world.Castellan.Position.Y)));
        // Há onde construir o Poço: uma célula livre encostada na água.
        bool wellSpot = false;
        for (int z = 0; z < world.Grid.Height && !wellSpot; z++)
            wellSpot = world.TouchesWater(new GridPos(3, z)) && !world.IsSolid(new GridPos(3, z));
        Assert.True(wellSpot);
    }

    private static string Contents(Inventory inventory) =>
        string.Join(", ", inventory.Counts.Where(p => p.Value > 0).Select(p => $"{p.Value} {p.Key}"));

    private static string EnergyStates(Building b) => b.Machine!.Waiting?.ToString() ?? "trabalhando";
}
