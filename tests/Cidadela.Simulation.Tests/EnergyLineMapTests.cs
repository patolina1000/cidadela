using System.Linq;
using Xunit;
using Xunit.Abstractions;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Teste A (data/maps/linha_energia.json): as duas linhas sem esteiras, 9 aldeões Inteligência 1 com ladainhas prontas
/// de data/ladainhas.json, andando sozinhas. Teste B (data/maps/linha_energia_zero.json): nada construído, zero aldeões.
/// </summary>
public class EnergyLineMapTests
{
    private const int Minute = 60 * SimClock.TicksPerSecond;

    private readonly ITestOutputHelper _output;

    public EnergyLineMapTests(ITestOutputHelper output) => _output = output;

    private static SimWorld Load() => MapLoader.Parse(TestWorlds.DataFile("maps/linha_energia.json"), TestWorlds.RealData(), TestWorlds.RealLitanies());

    [Fact]
    public void EveryVillagerCarriesALitanyItCanLearnAndEverythingIsPowered()
    {
        SimWorld world = Load();
        world.Tick();
        Assert.Equal(9, world.Villagers.Count);
        Assert.All(world.Villagers, v =>
        {
            Assert.NotNull(v.Litany);
            Assert.Equal(1, v.Intelligence);
            Assert.Equal(LitanyFit.Ok, v.CanLearn(v.Litany!));
        });
        Assert.Single(world.ManaNetworks);
        foreach (Building b in world.Buildings.Where(b => b.Type.Mana is not null))
            Assert.NotNull(b.Network);
    }

    [Fact]
    public void BothLinesRunAloneAndAVillagerIsBornEvery150Seconds()
    {
        SimWorld world = Load();
        Building crystal = world.Buildings.Single(b => b.Kind == "mother_crystal");
        var births = new System.Collections.Generic.List<long>();
        float supply = 0f, demand = 0f;
        for (int t = 0; t < 20 * Minute; t++)
        {
            int before = crystal.VillagersFormed;
            world.Tick();
            supply += world.ManaNetworks.Single().Supply;
            demand += world.ManaNetworks.Single().Demand;
            if (crystal.VillagersFormed > before)
                births.Add(world.TickCount);
        }
        _output.WriteLine($"gera {supply / (20 * Minute):0.0}/s, pede {demand / (20 * Minute):0.0}/s, nascimentos (s): "
            + string.Join(", ", births.Select(b => b / SimClock.TicksPerSecond)));
        Assert.True(births.Count >= 6, $"só {births.Count} aldeões em 20 min");
        for (int i = 1; i < births.Count; i++)
            Assert.InRange(births[i] - births[i - 1], 150 * SimClock.TicksPerSecond, 160 * SimClock.TicksPerSecond);
        Assert.True(supply > demand * 1.3f, "a mana precisa sobrar com 2 Relicários");
        Assert.Equal(20f, world.ManaNetworks.Single().Supply); // os dois Relicários acesos no fim
    }

    [Fact]
    public void WithOneReliquaryVillagersStillAreBorn()
    {
        // O veio da Mina 1 (300 cristais) acaba por volta dos 26 min: daí em diante só o Relicário 2 gera.
        SimWorld world = Load();
        Building crystal = world.Buildings.Single(b => b.Kind == "mother_crystal");
        TestWorlds.Run(world, 32 * Minute);
        Assert.True(world.BuildingAt(new GridPos(6, 3))!.Machine!.Exhausted);
        int formed = crystal.VillagersFormed;
        float supply = 0f, demand = 0f;
        for (int t = 0; t < 10 * Minute; t++)
        {
            world.Tick();
            supply += world.ManaNetworks.Single().Supply;
            demand += world.ManaNetworks.Single().Demand;
        }
        _output.WriteLine($"com 1 Relicário: gera {supply / (10 * Minute):0.0}/s, pede {demand / (10 * Minute):0.0}/s, "
            + $"{crystal.VillagersFormed - formed} aldeões em 10 min");
        Assert.True(crystal.VillagersFormed - formed >= 3);
        Assert.True(supply >= demand);
    }

    [Fact]
    public void NewbornsWithoutALitanyStayPut()
    {
        SimWorld world = Load();
        TestWorlds.Run(world, 6 * Minute);
        var newborns = world.Villagers.Where(v => v.Litany is null).ToList();
        Assert.NotEmpty(newborns);
        Assert.All(newborns, v => Assert.True(v.Blank));
        var cells = newborns.Select(v => v.Cell).ToList();
        TestWorlds.Run(world, Minute);
        Assert.Equal(cells, newborns.Select(v => v.Cell).ToList());
        Assert.All(newborns, v => Assert.Equal(VillagerStatus.NoLitany, v.Status));
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
