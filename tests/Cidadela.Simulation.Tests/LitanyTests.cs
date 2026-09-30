using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>O interpretador das ladainhas (docs/ladainhas.md): um comando por vez, repete do início, trava com motivo.</summary>
public class LitanyTests
{
    private static int Seconds(float s) => (int)MathF.Round(s * SimClock.TicksPerSecond);

    private static LitanyLibrary Library(string json) => LitanyLibrary.Parse(json, TestWorlds.Data());

    /// <summary>Mapa de teste 20×20 com um aldeão em (5, 5) carregando a ladainha "l".</summary>
    private static SimWorld World(string commands, string buildings = "[]") => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 18, "z": 18 }, "buildings": {{buildings}},
          "villagers": [{ "x": 5, "z": 5, "litany": "l" }] }
        """, TestWorlds.Data(), Library($$"""{ "l": { "commands": [{{commands}}] } }"""));

    [Fact]
    public void WithoutALitanyAVillagerStaysStill()
    {
        SimWorld world = TestWorlds.Open(villagers: """[{ "x": 5, "z": 5 }]""");
        TestWorlds.Run(world, Seconds(10f));
        Assert.Equal(new GridPos(5, 5), world.Villagers[0].Cell);
    }

    [Fact]
    public void RepeatsFromTheStartForever()
    {
        SimWorld world = World("""{ "do": "goto", "cell": [9, 5] }, { "do": "goto", "cell": [5, 5] }""");
        Villager v = world.Villagers[0];
        var seen = new List<GridPos>();
        for (int i = 0; i < Seconds(12f); i++)
        {
            world.Tick();
            if (seen.Count == 0 || seen[^1] != v.Cell)
                seen.Add(v.Cell);
        }
        // Vai e volta mais de uma vez (velocidade de teste 5 cél/s: 4 células em 0,8 s).
        Assert.True(seen.FindAll(c => c == new GridPos(9, 5)).Count >= 3);
        Assert.True(seen.FindAll(c => c == new GridPos(5, 5)).Count >= 3);
        Assert.Equal(VillagerStatus.Chanting, v.Status);
    }

    [Fact]
    public void WaitCountsItsSeconds()
    {
        SimWorld world = World("""{ "do": "wait", "seconds": 2 }, { "do": "goto", "cell": [9, 5] }""");
        Villager v = world.Villagers[0];
        TestWorlds.Run(world, Seconds(2f) - 1);
        Assert.Equal(0, v.CommandIndex);
        Assert.Equal(new GridPos(5, 5), v.Cell);
        TestWorlds.Run(world, 1);
        Assert.Equal(1, v.CommandIndex);
    }

    [Fact]
    public void GoToABuildingStopsBesideIt()
    {
        SimWorld world = World("""{ "do": "goto", "building": [12, 5] }, { "do": "wait", "seconds": 60 }""",
            """[{ "kind": "chest", "x": 12, "z": 5 }]""");
        TestWorlds.Run(world, Seconds(5f));
        Villager v = world.Villagers[0];
        Assert.Equal(1, v.CommandIndex);
        Assert.True(Math.Abs(v.Cell.X - 12) <= 1 && Math.Abs(v.Cell.Z - 5) <= 1);
    }

    [Fact]
    public void NoPathStucksWithAReasonAndRetriesLater()
    {
        // Célula cercada de baús: sem caminho.
        string walls = "[" + string.Join(", ", new[] { (14, 9), (14, 11), (13, 10), (15, 10), (13, 9), (15, 9), (13, 11), (15, 11) }
            .Select(c => $$"""{ "kind": "chest", "x": {{c.Item1}}, "z": {{c.Item2}} }""")) + "]";
        SimWorld world = World("""{ "do": "goto", "cell": [14, 10] }""", walls);
        Villager v = world.Villagers[0];
        world.Tick();
        Assert.Equal(LitanyStuck.NoPath, v.Stuck);
        Assert.Equal(VillagerStatus.Stuck, v.Status);
        TestWorlds.Run(world, SimClock.TicksPerSecond + 1);
        Assert.Equal(LitanyStuck.NoPath, v.Stuck); // tentou de novo e travou de novo: o motivo continua

        // Abrindo um lado, ele tenta de novo (espera 1 s, 2 s, 4 s...) e chega.
        world.Castellan.PlaceAt(new Vector2(16f, 12f));
        world.Enqueue(new DeconstructCommand(new GridPos(15, 10)));
        TestWorlds.Run(world, Seconds(10f));
        Assert.Null(v.Stuck);
        Assert.Equal(new GridPos(14, 10), v.Cell);
    }

    [Fact]
    public void IntelligenceOneTakesUpToSixCommands()
    {
        string Commands(int n) => string.Join(", ", Enumerable.Repeat("""{ "do": "wait", "seconds": 1 }""", n));
        LitanyLibrary library = Library($$"""{ "six": { "commands": [{{Commands(6)}}] }, "seven": { "commands": [{{Commands(7)}}] } }""");
        SimWorld world = TestWorlds.Open(villagers: """[{ "x": 5, "z": 5 }]""");
        Villager v = world.Villagers[0];
        Assert.Equal(LitanyFit.Ok, v.CanLearn(library["six"]));
        Assert.Equal(LitanyFit.TooLong, v.CanLearn(library["seven"]));
        world.Enqueue(new TeachLitanyCommand(v.Id, library["seven"]));
        world.Tick();
        Assert.Null(v.Litany); // recusou
        v.Intelligence = 2;
        Assert.Equal(LitanyFit.Ok, v.CanLearn(library["seven"])); // 12 comandos na Inteligência 2
    }

    [Theory]
    [InlineData("""{ "do": "dance" }""", "dance")]
    [InlineData("""{ "do": "take", "building": [1, 1] }""", "item")]
    [InlineData("""{ "do": "take", "item": "gold", "building": [1, 1] }""", "gold")]
    [InlineData("""{ "do": "wait" }""", "seconds")]
    [InlineData("""{ "do": "gather", "resource": "wood" }""", "near")]
    public void InvalidLitaniesAreRejectedWithAClearMessage(string command, string mentions)
    {
        var e = Assert.Throws<FormatException>(() => Library($$"""{ "l": { "commands": [{{command}}] } }"""));
        Assert.Contains(mentions, e.Message);
    }

    [Fact]
    public void AMapVillagerWithAnUnknownLitanyIsRejected()
    {
        Assert.Throws<FormatException>(() => MapLoader.Parse("""
            { "width": 10, "height": 10, "castellan": { "x": 1, "z": 1 }, "villagers": [{ "x": 5, "z": 5, "litany": "nenhuma" }] }
            """, TestWorlds.Data(), LitanyLibrary.Empty));
    }

    [Fact]
    public void AgilityAddsTenPercentPerPointAboveOne()
    {
        SimWorld world = World("""{ "do": "goto", "cell": [15, 5] }""");
        Villager v = world.Villagers[0];
        world.Tick();
        float baseSpeed = v.Speed;
        v.Agility = 3;
        world.Tick();
        Assert.Equal(baseSpeed * 1.2f, v.Speed, 3);
    }
}
