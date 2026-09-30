using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Ações à mão da protagonista (docs/linha_energia.md) com os números do jogo: coletar, arrancar, purificar, operar.</summary>
public class CastellanHandTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    private static SimWorld World(string resources = "[]", string buildings = "[]", string villagers = "[]") => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 5, "z": 5 },
          "resources": {{resources}}, "buildings": {{buildings}}, "villagers": {{villagers}} }
        """, TestWorlds.RealData());

    [Theory]
    [InlineData("wood", 2f)]
    [InlineData("stone", 2f)]
    [InlineData("rotten_shard", 4f)]
    public void GatheringTakesTheTimeOfTheSpec(string kind, float seconds)
    {
        SimWorld world = World($$"""[{ "kind": "{{kind}}", "x": 6, "z": 5 }]""");
        world.Enqueue(new GatherCommand(new GridPos(6, 5)));
        TestWorlds.Run(world, Seconds(seconds) - 1);
        Assert.Equal(0, world.Castellan.Inventory.Count(kind));
        TestWorlds.Run(world, 2);
        Assert.Equal(1, world.Castellan.Inventory.Count(kind));
    }

    [Fact]
    public void PurifyingByHandTurnsTwoRottenIntoOnePureInSixSeconds()
    {
        SimWorld world = World();
        world.Castellan.Inventory.Add("rotten_shard", 5);
        world.Enqueue(new HandCraftCommand("purify"));
        world.Enqueue(new HandCraftCommand("purify"));
        world.Enqueue(new HandCraftCommand("purify")); // o terceiro não tem podres suficientes
        TestWorlds.Run(world, Seconds(6f) + 1);
        Assert.Equal(1, world.Castellan.Inventory.Count("pure_shard"));
        TestWorlds.Run(world, Seconds(12f));
        Assert.Equal(2, world.Castellan.Inventory.Count("pure_shard"));
        Assert.Equal(1, world.Castellan.Inventory.Count("rotten_shard"));
        Assert.Equal(0, world.Castellan.HandQueue);
        Assert.Equal(0, world.Castellan.Inventory.Count("water_jar")); // sem água
    }

    [Fact]
    public void WalkingPausesTheHandPurificationWithoutLosingIt()
    {
        SimWorld world = World();
        world.Castellan.Inventory.Add("rotten_shard", 2);
        world.Enqueue(new HandCraftCommand("purify"));
        TestWorlds.Run(world, Seconds(3f));
        TestWorlds.Move(world, 1f, 0f, ticks: Seconds(2f));
        TestWorlds.Move(world, 0f, 0f, ticks: 1);
        Assert.Equal(0, world.Castellan.Inventory.Count("pure_shard"));
        Assert.True(world.Castellan.HandBusy);
        TestWorlds.Run(world, Seconds(3f) + 1);
        Assert.Equal(1, world.Castellan.Inventory.Count("pure_shard"));
    }

    /// <summary>Purificador com mana (torre e Relicário cheio) e entradas para 2 ciclos, encostado nela.</summary>
    private static SimWorld PoweredPurifier(string villagers = "[]")
    {
        SimWorld world = World(buildings: """
            [{ "kind": "mana_tower", "x": 8, "z": 8 }, { "kind": "reliquary", "x": 9, "z": 9, "items": { "pure_shard": 5 } },
             { "kind": "purifier", "x": 6, "z": 6 }]
            """, villagers: villagers);
        MachineState purifier = world.BuildingAt(new GridPos(6, 6))!.Machine!;
        purifier.Input.Add("rotten_shard", 4);
        purifier.Input.Add("water_jar", 2);
        return world;
    }

    [Fact]
    public void PressingENextToAMachineOperatesItAndPressingAgainLeaves()
    {
        SimWorld world = PoweredPurifier();
        Building purifier = world.BuildingAt(new GridPos(6, 6))!;
        world.Enqueue(new OperatePostCommand());
        TestWorlds.Run(world, Seconds(10f) + 5);
        Assert.Same(purifier, world.Castellan.Post);
        Assert.Equal(1, purifier.Machine!.Output.Count("pure_shard"));

        world.Enqueue(new OperatePostCommand());
        TestWorlds.Run(world, Seconds(12f));
        Assert.Null(world.Castellan.Post);
        Assert.Equal(1, purifier.Machine.Output.Count("pure_shard")); // o 2º ciclo parou no meio
        Assert.Equal(MachineWait.PostsEmpty, purifier.Machine.Waiting);
    }

    [Fact]
    public void WalkingLeavesThePost()
    {
        SimWorld world = PoweredPurifier();
        world.Enqueue(new OperatePostCommand());
        world.Tick();
        Assert.NotNull(world.Castellan.Post);
        TestWorlds.Move(world, -1f, 0f, ticks: 2);
        Assert.Null(world.Castellan.Post);
        Assert.Null(world.BuildingAt(new GridPos(6, 6))!.CastellanSlot);
    }

    [Fact]
    public void FarFromAnyMachineENothingHappens()
    {
        SimWorld world = PoweredPurifier();
        world.Castellan.PlaceAt(new Vector2(14f, 14f));
        world.Enqueue(new OperatePostCommand());
        world.Tick();
        Assert.Null(world.Castellan.Post);
    }

    [Fact]
    public void APostTakenByAVillagerIsNotFree()
    {
        SimWorld world = PoweredPurifier("""[{ "x": 6, "z": 7 }]""");
        TestWorlds.Run(world, 2);
        world.Enqueue(new OperatePostCommand());
        world.Tick();
        Assert.Null(world.Castellan.Post);
    }

    [Fact]
    public void WhenSheLeavesAnIdleVillagerTakesThePost()
    {
        // Ela ocupa o posto antes do aldeão chegar ao mapa? Não: o aldeão nasce depois e fica livre enquanto ela opera.
        SimWorld world = PoweredPurifier();
        world.Enqueue(new OperatePostCommand());
        world.Tick();
        Villager villager = world.AddVillager(new Vector2(12f, 12f));
        world.AssignIdleWorkers();
        Assert.Null(villager.Home);
        TestWorlds.Move(world, -1f, 0f, ticks: 2);
        Assert.Same(world.BuildingAt(new GridPos(6, 6)), villager.Home);
    }
}
