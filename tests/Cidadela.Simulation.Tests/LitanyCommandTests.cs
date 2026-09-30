using System;
using System.Linq;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Os comandos da Inteligência 1 (docs/ladainhas.md) com os dados do jogo: pegar, pôr, colher, cavar, operar.</summary>
public class LitanyCommandTests
{
    private static int Seconds(float s) => (int)MathF.Round(s * SimClock.TicksPerSecond);

    /// <summary>
    /// Mapa 24×20 com água em x 0–1, margem em x = 2; torres (10, 6) e (4, 6) com Relicário cheio (9, 7); baús A (12, 10) e B (16, 10);
    /// as construções, recursos e aldeões dados. Cada aldeão: { "x", "z", "litany": nome }; as ladainhas vêm de <paramref name="litanies"/>.
    /// </summary>
    private static SimWorld World(string litanies, string villagers, string buildings = "", string resources = "[]") => MapLoader.Parse($$"""
        { "width": 24, "height": 20, "castellan": { "x": 20, "z": 18 },
          "resources": {{resources}},
          "buildings": [{ "kind": "mana_tower", "x": 10, "z": 6 }, { "kind": "mana_tower", "x": 4, "z": 6 }, { "kind": "reliquary", "x": 9, "z": 7, "items": { "pure_shard": 12 } },
                        { "kind": "chest", "x": 12, "z": 10 }, { "kind": "chest", "x": 16, "z": 10 }{{buildings}}],
          "villagers": {{villagers}},
          "terrain": { "default": "grass", "patches": [{ "kind": "water", "x": 0, "z": 0, "width": 2, "height": 20 },
                                                      { "kind": "bank", "x": 2, "z": 0, "width": 1, "height": 20 }] } }
        """, TestWorlds.RealData(), LitanyLibrary.Parse(litanies, TestWorlds.RealData()));

    private static Inventory ChestA(SimWorld w) => w.BuildingAt(new GridPos(12, 10))!.Storage!;
    private static Inventory ChestB(SimWorld w) => w.BuildingAt(new GridPos(16, 10))!.Storage!;

    private const string Move = """
        { "move": { "commands": [{ "do": "take", "item": "ITEM", "building": [12, 10] }, { "do": "put", "item": "ITEM", "building": [16, 10] }] } }
        """;

    [Fact]
    public void TakeAndPutMoveLightItemsTenAtATime()
    {
        SimWorld world = World(Move.Replace("ITEM", "pure_shard"), """[{ "x": 14, "z": 12, "litany": "move" }]""");
        ChestA(world).Add("pure_shard", 25);
        Villager v = world.Villagers[0];
        int most = 0;
        for (int i = 0; i < Seconds(40f); i++)
        {
            world.Tick();
            most = Math.Max(most, v.CarryingCount);
        }
        Assert.Equal(10, most);
        Assert.Equal(25, ChestB(world).Count("pure_shard"));
    }

    [Fact]
    public void HeavyItemsGoOnePerPointOfStrength()
    {
        SimWorld world = World(Move.Replace("ITEM", "stone"), """[{ "x": 14, "z": 12, "litany": "move" }]""");
        ChestA(world).Add("stone", 6);
        Villager v = world.Villagers[0];
        int most = 0;
        for (int i = 0; i < Seconds(20f); i++)
        {
            world.Tick();
            most = Math.Max(most, v.CarryingCount);
        }
        Assert.Equal(1, most);
        Assert.True(ChestB(world).Count("stone") >= 2);
    }

    [Fact]
    public void TakeFromAMachineOutputAndPutIntoAMachineInput()
    {
        SimWorld world = World("""
            { "l": { "commands": [{ "do": "take", "item": "water_jar", "building": [2, 8] }, { "do": "put", "item": "water_jar", "building": [11, 8] }] } }
            """, """[{ "x": 6, "z": 8, "litany": "l" }]""", """, { "kind": "well", "x": 2, "z": 8 }, { "kind": "purifier", "x": 11, "z": 8 }""");
        world.BuildingAt(new GridPos(2, 8))!.Machine!.Output.Add("water_jar", 7);
        TestWorlds.Run(world, Seconds(40f));
        Assert.Equal(5, world.BuildingAt(new GridPos(11, 8))!.Machine!.Input.Count("water_jar")); // cabem 5 (5 ciclos)
    }

    [Theory]
    [InlineData("""{ "do": "take", "item": "stone", "building": [12, 10] }""", LitanyStuck.SourceEmpty)]
    [InlineData("""{ "do": "take", "item": "stone", "building": [5, 5] }""", LitanyStuck.NoPlace)]
    [InlineData("""{ "do": "gather", "resource": "wood", "near": [14, 12], "radius": 3 }""", LitanyStuck.NoResource)]
    [InlineData("""{ "do": "operate", "building": [12, 10] }""", LitanyStuck.NoPost)]
    public void EveryFailureHasAReason(string command, LitanyStuck reason)
    {
        SimWorld world = World($$"""{ "l": { "commands": [{{command}}] } }""", """[{ "x": 14, "z": 12, "litany": "l" }]""");
        TestWorlds.Run(world, 3);
        Assert.Equal(reason, world.Villagers[0].Stuck);
        Assert.Equal(VillagerStatus.Stuck, world.Villagers[0].Status);
    }

    [Fact]
    public void PuttingWhatTheMachineDoesNotUseOrIntoAFullOneStucks()
    {
        SimWorld world = World("""
            { "wood": { "commands": [{ "do": "put", "item": "wood", "building": [11, 8] }] },
              "rot":  { "commands": [{ "do": "put", "item": "rotten_shard", "building": [11, 8] }] } }
            """, """[{ "x": 14, "z": 12, "litany": "wood" }, { "x": 14, "z": 14, "litany": "rot" }]""", """, { "kind": "purifier", "x": 11, "z": 8 }""");
        foreach (Villager v in world.Villagers)
            v.GiveForTests(v.Litany!.Name == "wood" ? "wood" : "rotten_shard", 1);
        world.BuildingAt(new GridPos(11, 8))!.Machine!.Input.Add("rotten_shard", 10); // cheia (5 ciclos)
        TestWorlds.Run(world, 3);
        Assert.Equal(LitanyStuck.NotAccepted, world.Villagers.Single(v => v.Litany!.Name == "wood").Stuck);
        Assert.Equal(LitanyStuck.TargetFull, world.Villagers.Single(v => v.Litany!.Name == "rot").Stuck);
    }

    [Fact]
    public void PuttingWithNothingInHandMovesOn()
    {
        // O lugar anterior pegou tudo: "pôr" sem o item na mão segue a ladainha (não trava para sempre).
        SimWorld world = World("""{ "l": { "commands": [{ "do": "put", "item": "stone", "building": [16, 10] }, { "do": "wait", "seconds": 30 }] } }""",
            """[{ "x": 14, "z": 12, "litany": "l" }]""");
        TestWorlds.Run(world, 3);
        Assert.Null(world.Villagers[0].Stuck);
        Assert.Equal(1, world.Villagers[0].CommandIndex);
    }

    [Fact]
    public void TakingFromAnEmptyPlaceMovesOnIfHandsAlreadyHaveTheItem()
    {
        SimWorld world = World("""{ "l": { "commands": [{ "do": "take", "item": "pure_shard", "building": [12, 10] }, { "do": "wait", "seconds": 30 }] } }""",
            """[{ "x": 14, "z": 12, "litany": "l" }]""");
        world.Villagers[0].GiveForTests("pure_shard", 3);
        TestWorlds.Run(world, 3);
        Assert.Null(world.Villagers[0].Stuck);
        Assert.Equal(1, world.Villagers[0].CommandIndex);
    }

    [Fact]
    public void OperatingUntilTheOutputIsFullWaitsForTheInput()
    {
        // Purificador sem insumo: "até faltar insumo" sai logo; "até a saída encher" fica no posto esperando.
        SimWorld world = World("""
            { "full":  { "commands": [{ "do": "operate", "building": [11, 8], "until": "full" }, { "do": "wait", "seconds": 60 }] },
              "empty": { "commands": [{ "do": "operate", "building": [13, 8], "until": "empty" }, { "do": "wait", "seconds": 60 }] } }
            """, """[{ "x": 11, "z": 9, "litany": "full" }, { "x": 13, "z": 9, "litany": "empty" }]""",
            """, { "kind": "purifier", "x": 11, "z": 8 }, { "kind": "purifier", "x": 13, "z": 8 }""");
        TestWorlds.Run(world, Seconds(3f));
        Villager waiting = world.Villagers.Single(v => v.Litany!.Name == "full");
        Villager left = world.Villagers.Single(v => v.Litany!.Name == "empty");
        Assert.Equal(VillagerTask.AtPost, waiting.Task);
        Assert.Equal(0, waiting.CommandIndex);
        Assert.Equal(1, left.CommandIndex);
        // Com insumo para 5 ciclos, a saída enche e ele solta o posto.
        MachineState p = world.BuildingAt(new GridPos(11, 8))!.Machine!;
        for (int i = 0; i < 5; i++)
        {
            p.Input.Add("rotten_shard", 2);
            p.Input.Add("water_jar", 1);
            TestWorlds.Run(world, Seconds(10.5f));
        }
        Assert.Equal(5, p.Output.Count("pure_shard"));
        TestWorlds.Run(world, 5);
        Assert.Equal(1, waiting.CommandIndex);
    }

    [Fact]
    public void HandsFullOfAnotherItemStucks()
    {
        SimWorld world = World("""{ "l": { "commands": [{ "do": "take", "item": "pure_shard", "building": [12, 10] }] } }""",
            """[{ "x": 14, "z": 12, "litany": "l" }]""");
        ChestA(world).Add("pure_shard", 5);
        Villager v = world.Villagers[0];
        v.GiveForTests("stone", 1);
        TestWorlds.Run(world, 3);
        Assert.Equal(LitanyStuck.HandsFull, v.Stuck);
    }

    [Fact]
    public void TwoVillagersNeverGatherTheSameTree()
    {
        SimWorld world = World("""
            { "l": { "commands": [{ "do": "gather", "resource": "wood", "near": [14, 14], "radius": 6 }, { "do": "put", "item": "wood", "building": [16, 10] }] } }
            """, """[{ "x": 14, "z": 12, "litany": "l" }, { "x": 15, "z": 12, "litany": "l" }]""",
            resources: """[{ "kind": "wood", "x": 14, "z": 15 }, { "kind": "wood", "x": 18, "z": 16 }]""");
        TestWorlds.Run(world, 3);
        Assert.NotNull(world.Villagers[0].Target);
        Assert.NotNull(world.Villagers[1].Target);
        Assert.NotSame(world.Villagers[0].Target, world.Villagers[1].Target);
        TestWorlds.Run(world, Seconds(60f)); // 1 tora por viagem (Força 1), a 0,8 cél/s
        Assert.True(ChestB(world).Count("wood") >= 4, $"só {ChestB(world).Count("wood")} toras");
    }

    [Fact]
    public void TwoVillagersDoNotCountOnTheSameItem()
    {
        SimWorld world = World(Move.Replace("ITEM", "stone"), """[{ "x": 14, "z": 12, "litany": "move" }, { "x": 15, "z": 12, "litany": "move" }]""");
        ChestA(world).Add("stone", 1);
        TestWorlds.Run(world, 2);
        Assert.Single(world.Villagers, v => v.Stuck == LitanyStuck.SourceEmpty);
    }

    [Fact]
    public void DiggingTheBankGivesClay()
    {
        SimWorld world = World("""
            { "l": { "commands": [{ "do": "gather", "resource": "clay", "near": [2, 10] }, { "do": "put", "item": "clay", "building": [12, 10] }] } }
            """, """[{ "x": 4, "z": 10, "litany": "l" }]""");
        TestWorlds.Run(world, Seconds(60f)); // 1 argila por viagem, 4,5 s cavando, 10 células até o baú
        Assert.True(ChestA(world).Count("clay") >= 2, $"só {ChestA(world).Count("clay")} argilas");
    }

    [Fact]
    public void OperatingKeepsTheMachineRunningUntilTheOutputIsFull()
    {
        SimWorld world = World("""{ "op": { "commands": [{ "do": "operate", "building": [11, 5] }, { "do": "wait", "seconds": 30 }] } }""",
            """[{ "x": 13, "z": 5, "litany": "op" }]""", """, { "kind": "crystal_mine", "x": 11, "z": 5 }""",
            """[{ "kind": "rotten_shard", "x": 11, "z": 5 }]""");
        Building mine = world.BuildingAt(new GridPos(11, 5))!;
        Villager v = world.Villagers[0];
        TestWorlds.Run(world, Seconds(10f));
        Assert.Equal(VillagerTask.AtPost, v.Task);
        Assert.Same(mine, v.Home);
        TestWorlds.Run(world, Seconds(22f));
        Assert.Equal(5, mine.Machine!.Output.Count("rotten_shard")); // saída cheia
        Assert.Equal(1, v.CommandIndex); // largou o posto e foi esperar
        Assert.Null(v.Home);
        Assert.Null(mine.Crew[0]);
    }

    [Fact]
    public void ASecondOperatorFindsThePostTaken()
    {
        SimWorld world = World("""{ "op": { "commands": [{ "do": "operate", "building": [11, 5] }] } }""",
            """[{ "x": 13, "z": 5, "litany": "op" }, { "x": 13, "z": 6, "litany": "op" }]""", """, { "kind": "crystal_mine", "x": 11, "z": 5 }""",
            """[{ "kind": "rotten_shard", "x": 11, "z": 5 }]""");
        TestWorlds.Run(world, 3);
        Assert.Single(world.Villagers, v => v.Stuck == LitanyStuck.PostTaken);
    }

    [Fact]
    public void AShortLineRunsAloneWellToChest()
    {
        // Um opera o Poço; outro leva os jarros do Poço ao baú A.
        SimWorld world = World("""
            { "op":    { "commands": [{ "do": "operate", "building": [2, 8] }] },
              "carry": { "commands": [{ "do": "take", "item": "water_jar", "building": [2, 8] }, { "do": "put", "item": "water_jar", "building": [12, 10] }] } }
            """, """[{ "x": 3, "z": 8, "litany": "op" }, { "x": 6, "z": 9, "litany": "carry" }]""", """, { "kind": "well", "x": 2, "z": 8 }""");
        world.Castellan.PlaceAt(new Vector2(20f, 18f));
        TestWorlds.Run(world, Seconds(90f));
        Assert.True(ChestA(world).Count("water_jar") >= 8, $"só {ChestA(world).Count("water_jar")} jarros");
    }

    [Fact]
    public void StartingALitanyDropsTheLoadInTheNearestChest()
    {
        SimWorld world = World("""{ "l": { "commands": [{ "do": "wait", "seconds": 5 }] } }""", """[{ "x": 14, "z": 12 }]""");
        Villager v = world.Villagers[0];
        v.GiveForTests("stone", 1);
        world.Enqueue(new TeachLitanyCommand(v.Id, LitanyLibrary.Parse("""{ "l": { "commands": [{ "do": "wait", "seconds": 5 }] } }""", TestWorlds.RealData())["l"]));
        TestWorlds.Run(world, Seconds(5f));
        Assert.Equal(0, v.CarryingCount);
        Assert.Equal(1, ChestA(world).Count("stone") + ChestB(world).Count("stone"));
    }
}
