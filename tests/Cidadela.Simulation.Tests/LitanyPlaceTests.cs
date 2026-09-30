using System.Numerics;
using Xunit;
using static Cidadela.Simulation.Tests.TestWorlds;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Cabanas e Posto de Carregadores como LUGARES que a ladainha cita (ajuste 2 do Arthur, docs/ladainhas.md): a área de
/// busca e o estoque. Nunca dão ordem a ninguém. Dados de teste: cabana do lenhador com raio 8 e estoque 3.
/// </summary>
public class LitanyPlaceTests
{
    private static LitanyCommand GatherNear(string resource, int x, int z) =>
        new(LitanyVerb.Gather, new LitanyTarget(LitanyTargetKind.Resource, new GridPos(x, z), resource, 0f, Anchored: true));

    private static LitanyCommand Take(string item, int x, int z) =>
        new(LitanyVerb.Take, new LitanyTarget(LitanyTargetKind.Building, new GridPos(x, z)), item);

    [Fact]
    public void GatheringNearAHutSearchesInsideItsArea()
    {
        // Cabana em (14, 14), raio 8. Árvore A perto do aldeão mas fora da área; árvore B longe dele, dentro da área.
        SimWorld world = Open(x: 1, z: 1, resources: """[{ "kind": "wood", "x": 3, "z": 3 }, { "kind": "wood", "x": 12, "z": 12 }]""",
            buildings: """[{ "kind": "lumber_hut", "x": 14, "z": 14 }]""", villagers: """[{ "x": 2, "z": 2 }]""");
        Teach(world, world.Villagers[0], Litany(GatherNear("wood", 14, 14), Put("wood", 14, 14)));
        Run(world, 2);
        Assert.Equal(new GridPos(12, 12), world.Villagers[0].Target!.Cell);
        Run(world, 200);
        Assert.True(world.BuildingAt(new GridPos(14, 14))!.Workplace!.Stored.Count("wood") >= 1); // "ponha na Cabana"
    }

    [Fact]
    public void TheHutIsAStockToTakeFromUpToItsCapacity()
    {
        SimWorld world = Open(x: 1, z: 1, buildings: """[{ "kind": "lumber_hut", "x": 6, "z": 6 }, { "kind": "chest", "x": 10, "z": 6 }]""",
            villagers: """[{ "x": 8, "z": 8 }]""");
        world.BuildingAt(new GridPos(6, 6))!.Workplace!.Stored.Add("wood", 3);
        Teach(world, world.Villagers[0], Litany(Take("wood", 6, 6), Put("wood", 10, 6)));
        Run(world, 100);
        Assert.Equal(3, world.BuildingAt(new GridPos(10, 6))!.Storage!.Count("wood"));
    }

    [Fact]
    public void AFullHutRefusesMore()
    {
        SimWorld world = Open(x: 1, z: 1, buildings: """[{ "kind": "lumber_hut", "x": 6, "z": 6 }]""", villagers: """[{ "x": 8, "z": 8 }]""");
        world.BuildingAt(new GridPos(6, 6))!.Workplace!.Stored.Add("wood", 3); // capacidade 3
        world.Villagers[0].GiveForTests("wood", 1);
        Teach(world, world.Villagers[0], Litany(Put("wood", 6, 6)));
        Run(world, 3);
        Assert.Equal(LitanyStuck.TargetFull, world.Villagers[0].Stuck);
    }

    [Fact]
    public void TheCarrierPostIsAPlaceAndAStockToo()
    {
        SimWorld world = Open(x: 1, z: 1, resources: """[{ "kind": "wood", "x": 9, "z": 9 }]""",
            buildings: """[{ "kind": "carrier_post", "x": 6, "z": 6 }]""", villagers: """[{ "x": 7, "z": 8 }]""");
        Teach(world, world.Villagers[0], Litany(GatherNear("wood", 6, 6), Put("wood", 6, 6)));
        Run(world, 200);
        Assert.True(world.BuildingAt(new GridPos(6, 6))!.Storage!.Count("wood") >= 1);
    }

    [Fact]
    public void WhenTheCitedHutIsGoneTheLitanyStucks()
    {
        SimWorld world = Open(x: 5, z: 5, resources: """[{ "kind": "wood", "x": 9, "z": 9 }]""",
            buildings: """[{ "kind": "lumber_hut", "x": 6, "z": 6 }]""", villagers: """[{ "x": 12, "z": 12 }]""");
        Teach(world, world.Villagers[0], Litany(GatherNear("wood", 6, 6)));
        world.Enqueue(new DeconstructCommand(new GridPos(6, 6)));
        Run(world, 3);
        Assert.Equal(LitanyStuck.NoPlace, world.Villagers[0].Stuck);
    }

    [Fact]
    public void TeachingNearAHutRecordsTheHutAsThePlace()
    {
        SimWorld world = Open(x: 8, z: 8, resources: """[{ "kind": "wood", "x": 9, "z": 9 }]""",
            buildings: """[{ "kind": "lumber_hut", "x": 12, "z": 12 }]""", villagers: """[{ "x": 2, "z": 2 }]""");
        world.Enqueue(new StartTeachingCommand(world.Villagers[0].Id));
        world.Enqueue(new GatherCommand(new GridPos(9, 9)));
        world.Tick();
        LitanyCommand recorded = world.Teaching!.Commands[0];
        Assert.True(recorded.Target!.Anchored);
        Assert.Equal(new GridPos(12, 12), recorded.Target.Cell);
    }

    [Fact]
    public void AGatherCitingABuildingParsesFromJson()
    {
        LitanyLibrary library = LitanyLibrary.Parse("""
            { "l": { "commands": [{ "do": "gather", "resource": "wood", "building": [4, 4] }] } }
            """, Data());
        LitanyTarget t = library["l"].Commands[0].Target!;
        Assert.True(t.Anchored);
        Assert.Equal(new GridPos(4, 4), t.Cell);
    }
}
