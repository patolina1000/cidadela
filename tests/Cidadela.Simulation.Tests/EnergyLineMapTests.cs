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
    public void EverythingIsPoweredAndNobodyMovesWithoutALitany()
    {
        // O mapa será refeito com ladainhas (passo 11). Por ora: tudo na rede, e sem ladainha ninguém sai do lugar.
        SimWorld world = Load();
        var start = world.Villagers.Select(v => v.Cell).ToList();
        TestWorlds.Run(world, 5 * SimClock.TicksPerSecond);
        Assert.Single(world.ManaNetworks);
        foreach (Building b in world.Buildings.Where(b => b.Type.Mana is not null))
            Assert.NotNull(b.Network);
        Assert.Equal(start, world.Villagers.Select(v => v.Cell).ToList());
        Assert.All(world.Villagers, v => Assert.Null(v.Home));
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
