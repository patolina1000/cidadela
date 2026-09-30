using System;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Peso dos itens (docs/linha_energia.md, regras 3 e 7): pesado só nas costas, leve na esteira; carga por peso.</summary>
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
    public void CastellanCannotPutHeavyOnABelt()
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4, data: TestWorlds.RealData(),
            buildings: """[{ "kind": "belt", "x": 6, "z": 4, "direction": "east" }]""");
        world.Castellan.Inventory.Add("rotten_shard", 3);
        world.Castellan.Inventory.Add("pure_shard", 3);
        world.Enqueue(new InsertItemCommand(new GridPos(6, 4), "rotten_shard"));
        world.Tick();
        Assert.Empty(world.BuildingAt(new GridPos(6, 4))!.Belt!.Items);
        Assert.Equal(3, world.Castellan.Inventory.Count("rotten_shard"));

        world.Enqueue(new InsertItemCommand(new GridPos(6, 4), "pure_shard"));
        world.Tick();
        Assert.Single(world.BuildingAt(new GridPos(6, 4))!.Belt!.Items);
    }

    [Fact]
    public void HutDoesNotPushHeavyOntoABeltButFillsAChest()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), buildings: """
            [{ "kind": "lumber_hut", "x": 5, "z": 5, "direction": "east" },
             { "kind": "belt", "x": 6, "z": 5, "direction": "east" },
             { "kind": "lumber_hut", "x": 5, "z": 9, "direction": "east" },
             { "kind": "chest", "x": 6, "z": 9 }]
            """);
        Building beltHut = world.BuildingAt(new GridPos(5, 5))!, chestHut = world.BuildingAt(new GridPos(5, 9))!;
        beltHut.Workplace!.Stored.Add("wood", 4);
        chestHut.Workplace!.Stored.Add("wood", 4);
        TestWorlds.Run(world, 10);
        Assert.Empty(world.BuildingAt(new GridPos(6, 5))!.Belt!.Items);
        Assert.Equal(4, beltHut.Workplace.Stored.Count("wood"));
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
