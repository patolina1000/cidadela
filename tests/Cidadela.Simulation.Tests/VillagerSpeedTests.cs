using System;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Velocidade por patamares (decisão de 29/09/2026): patamar × bônus do piso × penalidade, presa ao teto.</summary>
public class VillagerSpeedTests
{
    private static SimWorld World(string buildings = "[]") =>
        TestWorlds.Open(x: 1, z: 18, buildings: buildings, villagers: """[{ "x": 2, "z": 2 }]""");

    [Fact]
    public void StartsAtTheBaseTier()
    {
        SimWorld world = World();
        world.Tick();
        Assert.Equal(0, world.Villagers[0].SpeedTier);
        Assert.Equal(5f, world.Villagers[0].Speed);
    }

    [Fact]
    public void TheTierCommandChangesEveryVillagerAndClampsToTheList()
    {
        SimWorld world = TestWorlds.Open(villagers: """[{ "x": 2, "z": 2 }, { "x": 5, "z": 5 }]""");
        world.Enqueue(new SetSpeedTierCommand(1));
        world.Tick();
        Assert.All(world.Villagers, v => Assert.Equal(6f, v.Speed));
        world.Enqueue(new SetSpeedTierCommand(99));
        world.Tick();
        Assert.All(world.Villagers, v => Assert.Equal(2, v.SpeedTier));
    }

    [Fact]
    public void ThePenaltyMultipliesByTheFactorFromTheJson()
    {
        // penaltySpeed 2,5 no base 5 = fator 0,5; no patamar 1 (6) dá 3.
        SimWorld world = World();
        world.Enqueue(new SetPenalizedCommand(true));
        world.Tick();
        Assert.Equal(2.5f, world.Villagers[0].Speed);
        world.Enqueue(new SetSpeedTierCommand(1));
        world.Tick();
        Assert.Equal(3f, world.Villagers[0].Speed, 3);
        world.Enqueue(new SetPenalizedCommand(false));
        world.Tick();
        Assert.Equal(6f, world.Villagers[0].Speed);
    }

    [Fact]
    public void TheCapLimitsTheFinalSpeed()
    {
        SimWorld world = World();
        world.Enqueue(new SetSpeedTierCommand(2)); // 8, acima do teto 7
        world.Tick();
        Assert.Equal(7f, world.Villagers[0].Speed);
    }

    [Fact]
    public void AFloorUnderTheVillagerMultipliesTheSpeed()
    {
        SimWorld world = World("""[{ "kind": "floor", "x": 2, "z": 2 }]""");
        world.Tick();
        Assert.Equal(6f, world.Villagers[0].Speed, 3); // 5 × 1,2
        Assert.Equal(1.2f, world.FloorBonusAt(new GridPos(2, 2)), 3);
        Assert.Equal(1f, world.FloorBonusAt(new GridPos(3, 3)));
    }

    [Fact]
    public void TheFinalSpeedDrivesTheMovement()
    {
        // Cabana e árvore como nos testes do aldeão; com o patamar 1 ele anda 6 células/s (0,3 por tick).
        SimWorld world = TestWorlds.Open(x: 1, z: 18, resources: """[{ "kind": "wood", "x": 12, "z": 4 }]""",
            buildings: """[{ "kind": "lumber_hut", "x": 4, "z": 4, "direction": "east" }]""", villagers: """[{ "x": 2, "z": 2 }]""");
        world.Enqueue(new SetSpeedTierCommand(1));
        TestWorlds.Run(world, 3);
        System.Numerics.Vector2 before = world.Villagers[0].Position;
        world.Tick();
        float moved = System.Numerics.Vector2.Distance(before, world.Villagers[0].Position);
        Assert.InRange(moved, 0.29f, 0.31f);
    }

    [Fact]
    public void RealDataHasThreeTiersPenaltyAndCap()
    {
        GameData data = GameData.Parse(TestWorlds.DataFile("items.json"), TestWorlds.DataFile("resources.json"),
            TestWorlds.DataFile("castellan.json"), TestWorlds.DataFile("villagers.json"), TestWorlds.DataFile("buildings.json"),
            TestWorlds.DataFile("recipes.json"));
        Assert.Equal(new[] { 0.8f, 1.0f, 1.2f }, data.Villagers.SpeedTiers);
        Assert.Equal(0.57f, data.Villagers.FinalSpeed(0, 1f, penalized: true), 3);
        Assert.Equal(1.5f, data.Villagers.MaxSpeed);
        Assert.Equal(1.2f, data.Villagers.FinalSpeed(5, 1f, penalized: false), 3); // patamar fora da lista prende no último
    }

    [Theory]
    [InlineData("""{ "speedTiers": [], "penaltySpeed": 0.5, "maxSpeed": 1.5, "gatherMultiplier": 1.0, "carry": { "pesado": 1, "leve": 10 } }""")]
    [InlineData("""{ "speedTiers": [1.0, 0.8], "penaltySpeed": 0.5, "maxSpeed": 1.5, "gatherMultiplier": 1.0, "carry": { "pesado": 1, "leve": 10 } }""")]
    [InlineData("""{ "speedTiers": [1.0], "penaltySpeed": 1.2, "maxSpeed": 1.5, "gatherMultiplier": 1.0, "carry": { "pesado": 1, "leve": 10 } }""")]
    [InlineData("""{ "speedTiers": [1.0], "penaltySpeed": 0.5, "maxSpeed": 0, "gatherMultiplier": 1.0, "carry": { "pesado": 1, "leve": 10 } }""")]
    public void InvalidSpeedDataIsRejected(string villagers)
    {
        Assert.Throws<FormatException>(() => GameData.Parse(TestWorlds.Items, TestWorlds.Resources, TestWorlds.CastellanStats,
            villagers, TestWorlds.Buildings, TestWorlds.Recipes));
    }
}
