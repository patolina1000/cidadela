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
        Assert.Equal(9, world.Villagers.Count(v => v.Home is not null)); // o mínimo das duas linhas (L3)
    }

    /// <summary>Roda o teste A por alguns minutos e devolve (geração média, consumo médio, pedido médio, nascimentos em s).</summary>
    private (float Supply, float Used, float Asked, System.Collections.Generic.List<float> Births) RunMinutes(SimWorld world, int minutes)
    {
        Building crystal = world.Buildings.Single(b => b.Kind == "mother_crystal");
        var births = new System.Collections.Generic.List<float>();
        float supply = 0f, used = 0f, asked = 0f;
        int formed = 0, ticks = minutes * 60 * SimClock.TicksPerSecond;
        for (int i = 0; i < ticks; i++)
        {
            world.Tick();
            ManaNetwork n = world.ManaNetworks.Single();
            supply += n.Supply;
            used += System.MathF.Min(n.Demand, n.Supply);
            asked += n.Demand;
            if (crystal.VillagersFormed > formed)
            {
                formed = crystal.VillagersFormed;
                births.Add(world.TickCount / (float)SimClock.TicksPerSecond);
            }
        }
        _output.WriteLine($"gera {supply / ticks:0.00}/s, consome {used / ticks:0.00}/s, pede {asked / ticks:0.00}/s; " +
            $"aldeões nascidos aos {string.Join(", ", births.Select(t => $"{t:0} s"))}");
        return (supply / ticks, used / ticks, asked / ticks, births);
    }

    [Fact]
    public void BothLinesRunAloneAndAVillagerIsBornEvery150Seconds()
    {
        SimWorld world = Load();
        (float supply, float used, _, var births) = RunMinutes(world, 15);
        Assert.True(births.Count >= 4, $"só {births.Count} aldeões em 15 min");
        for (int i = 1; i < births.Count; i++)
            Assert.InRange(births[i] - births[i - 1], 149f, 200f);
        Assert.True(supply > 19f, $"geração {supply}");
        Assert.True(used < supply, "faltou mana com 2 Relicários");
        Assert.Equal(9 + births.Count, world.Villagers.Count);
    }

    [Fact]
    public void WithOneReliquaryManaIsShort()
    {
        // A tensão da especificação: 1 Relicário (10/s) não sustenta as duas linhas.
        string json = TestWorlds.DataFile("maps/linha_energia.json")
            .Replace("""{ "kind": "reliquary", "x": 4, "z": 6, "items": { "pure_shard": 5 } },""", "");
        SimWorld world = MapLoader.Parse(json, TestWorlds.RealData());
        TestWorlds.Run(world, 5 * 60 * SimClock.TicksPerSecond);
        (float supply, _, float asked, var births) = RunMinutes(world, 10);
        Assert.True(asked > supply + 1f, $"pede {asked} para {supply}");
        Assert.NotEmpty(births); // mais devagar, mas forma
    }

    [Fact]
    public void NoBeltPointsIntoAMachine()
    {
        // Layout estilo Factorio (orientação do Arthur, 30/09): a esteira corre ao lado; só mariposa entra e sai.
        SimWorld world = Load();
        foreach (Building belt in world.Buildings.Where(b => b.Belt is not null))
            Assert.Null(world.BuildingAt(belt.Cell.Step(belt.Direction))?.Machine);
        foreach (Building machine in world.Buildings.Where(b => b.Machine is not null && b.Kind is not ("crystal_mine" or "clay_pit")))
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
        // E margem para cavar argila (linha 2).
        Assert.Contains(Enumerable.Range(0, world.Grid.Height), z => world.IsBank(new GridPos(3, z)));
    }

}
