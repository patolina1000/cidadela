using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Rede de mana (docs/linha_energia.md, regra 6), com dados de teste: torre (fio 7, área 5×5), gerador (10/s sempre) e
/// lâmpada (gasta 4/s sempre).
/// </summary>
public class ManaNetworkTests
{
    private static SimWorld World(string buildings)
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: buildings);
        world.Tick();
        return world;
    }

    private static string At(string kind, int x, int z) => $$"""{ "kind": "{{kind}}", "x": {{x}}, "z": {{z}} }""";

    [Fact]
    public void TowersSevenCellsApartLinkButEightDoNot()
    {
        SimWorld linked = World($"[{At("tower", 2, 10)}, {At("tower", 9, 10)}]");
        Assert.Single(linked.ManaNetworks);
        SimWorld apart = World($"[{At("tower", 2, 10)}, {At("tower", 10, 10)}]");
        Assert.Equal(2, apart.ManaNetworks.Count);
    }

    [Fact]
    public void DiagonalWireCountsTheRealDistance()
    {
        // (5, 5) de distância = 7,07 células: passa do fio de 7.
        Assert.Equal(2, World($"[{At("tower", 2, 2)}, {At("tower", 7, 7)}]").ManaNetworks.Count);
        Assert.Single(World($"[{At("tower", 2, 2)}, {At("tower", 6, 7)}]").ManaNetworks);
    }

    [Fact]
    public void TheAreaIsFiveByFive()
    {
        SimWorld world = World($"[{At("tower", 10, 10)}, {At("lamp", 12, 12)}, {At("lamp", 13, 10)}]");
        Assert.NotNull(world.BuildingAt(new GridPos(12, 12))!.Network);
        Assert.Null(world.BuildingAt(new GridPos(13, 10))!.Network);
    }

    [Fact]
    public void ShortageSlowsEveryConsumerByTheSameFraction()
    {
        // 10/s para 4 lâmpadas de 4/s = 16/s: todas recebem 10/16.
        SimWorld world = World($"[{At("tower", 10, 10)}, {At("generator", 8, 8)}, {At("lamp", 12, 8)}, {At("lamp", 12, 12)}, " +
            $"{At("lamp", 8, 12)}, {At("lamp", 11, 10)}]");
        ManaNetwork network = world.ManaNetworks.Single();
        Assert.Equal(10f, network.Supply);
        Assert.Equal(16f, network.Demand);
        Building[] lamps = world.Buildings.Where(b => b.Kind == "lamp").ToArray();
        Assert.Equal(4, lamps.Length);
        Assert.All(lamps, l => Assert.Equal(0.625f, l.ManaSatisfaction, 3));
    }

    [Fact]
    public void SeparateNetworksAreIndependent()
    {
        // Rede da esquerda: gerador e 1 lâmpada (sobra). Rede da direita: gerador e 4 lâmpadas (falta).
        SimWorld world = World($"[{At("tower", 3, 10)}, {At("generator", 2, 9)}, {At("lamp", 4, 9)}, " +
            $"{At("tower", 15, 10)}, {At("generator", 14, 9)}, {At("lamp", 16, 9)}, {At("lamp", 16, 11)}, {At("lamp", 14, 11)}, {At("lamp", 15, 12)}]");
        Assert.Equal(2, world.ManaNetworks.Count);
        Assert.Equal(1f, world.BuildingAt(new GridPos(4, 9))!.ManaSatisfaction);
        Assert.Equal(0.625f, world.BuildingAt(new GridPos(16, 9))!.ManaSatisfaction, 3);
    }

    [Fact]
    public void WithoutAGeneratorOrOutsideTheNetworkNothingArrives()
    {
        SimWorld world = World($"[{At("tower", 10, 10)}, {At("lamp", 11, 10)}, {At("lamp", 2, 2)}]");
        Assert.Equal(0f, world.BuildingAt(new GridPos(11, 10))!.ManaSatisfaction);
        Assert.Equal(0f, world.BuildingAt(new GridPos(2, 2))!.ManaSatisfaction);
    }

    [Fact]
    public void BuildingsWithoutManaAreNotSlowed()
    {
        SimWorld world = World($"[{At("kiln", 10, 10)}]");
        Assert.Equal(1f, world.BuildingAt(new GridPos(10, 10))!.ManaSatisfaction);
    }

    [Fact]
    public void NetworksAreRebuiltOnlyWhenABuildingChanges()
    {
        SimWorld world = World($"[{At("tower", 3, 3)}, {At("generator", 2, 2)}]");
        int rebuilds = world.ManaRebuilds;
        TestWorlds.Run(world, 50);
        Assert.Equal(rebuilds, world.ManaRebuilds);

        // A torre nova a 6 células liga a lâmpada à rede do gerador.
        world.Castellan.Inventory.Add("wood", 2);
        world.Enqueue(new BuildCommand("tower", new GridPos(9, 3), Direction.North));
        world.Enqueue(new BuildCommand("lamp", new GridPos(10, 4), Direction.North));
        world.Tick();
        Assert.Equal(rebuilds + 1, world.ManaRebuilds);
        Assert.Single(world.ManaNetworks);
        Assert.Equal(1f, world.BuildingAt(new GridPos(10, 4))!.ManaSatisfaction);

        world.Enqueue(new DeconstructCommand(new GridPos(9, 3)));
        world.Tick();
        Assert.Equal(0f, world.BuildingAt(new GridPos(10, 4))!.ManaSatisfaction);
    }
}
