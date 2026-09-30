using System;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Peso dos itens: carga por viagem, pesado 1 por ponto de Força e leve 10 (docs/ladainhas.md).</summary>
public class ItemWeightTests
{
    [Fact]
    public void RealItemsHaveTheWeightsOfTheSpec()
    {
        GameData data = TestWorlds.RealData();
        Assert.Equal(ItemWeight.Heavy, data.Item("wood").Weight);
        Assert.Equal(ItemWeight.Heavy, data.Item("stone").Weight);
        Assert.Equal(ItemWeight.Heavy, data.Item("rotten_shard").Weight);
        Assert.Equal(ItemWeight.Light, data.Item("pure_shard").Weight);
        Assert.Equal(ItemWeight.Light, data.Item("water_jar").Weight);
        Assert.Equal(ItemWeight.Heavy, data.Item("clay").Weight);
        Assert.Equal(ItemWeight.Heavy, data.Item("shell").Weight);
        Assert.Equal(7, data.Items.Count); // os itens antigos (minério, haste, lingote, espada) saíram
    }

    [Fact]
    public void HeavyCarryGrowsWithStrength()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), villagers: """[{ "x": 5, "z": 5 }]""");
        Villager v = world.Villagers[0];
        Assert.Equal(1, v.Strength); // nasce com Força 1
        Assert.Equal(1, v.CarryFor(world, "rotten_shard"));
        Assert.Equal(10, v.CarryFor(world, "pure_shard"));
        v.Strength = 3;
        Assert.Equal(3, v.CarryFor(world, "rotten_shard"));
        Assert.Equal(10, v.CarryFor(world, "pure_shard"));
    }

    [Fact]
    public void RealCarryIsOneHeavyOrTenLight()
    {
        VillagerStats stats = TestWorlds.RealData().Villagers;
        Assert.Equal(1, stats.CarryFor(ItemWeight.Heavy));
        Assert.Equal(10, stats.CarryFor(ItemWeight.Light));
    }

    [Theory]
    [InlineData("medio")]
    [InlineData("")]
    [InlineData("leveza")]
    public void MediumOrUnknownWeightIsRejected(string weight)
    {
        string items = $$"""{ "wood": { "name": "Madeira", "color": "6B5B4B", "peso": "{{weight}}" } }""";
        Assert.Throws<FormatException>(() => GameData.Parse(items, """{ "wood": { "gatherSeconds": 1.0, "amount": 1 } }""",
            TestWorlds.CastellanStats, TestWorlds.VillagerStats, "{}", "{}"));
    }

    [Fact]
    public void HutFillsTheChestInFront()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), buildings: """
            [{ "kind": "lumber_hut", "x": 5, "z": 9, "direction": "east" }, { "kind": "chest", "x": 6, "z": 9 }]
            """);
        Building chestHut = world.BuildingAt(new GridPos(5, 9))!;
        chestHut.Workplace!.Stored.Add("wood", 4);
        TestWorlds.Run(world, 10);
        Assert.Equal(4, world.BuildingAt(new GridPos(6, 9))!.Storage!.Count("wood"));
    }

    [Fact]
    public void LumberjackCarriesOneLogPerTrip()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(),
            resources: """[{ "kind": "wood", "x": 8, "z": 5 }]""",
            buildings: """[{ "kind": "lumber_hut", "x": 5, "z": 5 }]""", villagers: """[{ "x": 6, "z": 5 }]""");
        Villager v = world.Villagers[0];
        for (int i = 0; i < 60 * SimClock.TicksPerSecond && v.Task != VillagerTask.ReturningHome; i++)
            world.Tick();
        Assert.Equal(VillagerTask.ReturningHome, v.Task);
        Assert.Equal(1, v.CarryingCount);
    }
}
