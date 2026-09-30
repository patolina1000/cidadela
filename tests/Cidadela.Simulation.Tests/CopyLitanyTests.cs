using System;
using System.Linq;
using Xunit;
using static Cidadela.Simulation.Tests.TestWorlds;

namespace Cidadela.Simulation.Tests;

/// <summary>Copiar ladainhas (docs/ladainhas.md): de graça, para vários, cada um independente; a Inteligência decide.</summary>
public class CopyLitanyTests
{
    private static SimWorld World() => Open(x: 1, z: 18, buildings: """[{ "kind": "chest", "x": 4, "z": 4 }]""",
        resources: """[{ "kind": "wood", "x": 7, "z": 4 }, { "kind": "wood", "x": 4, "z": 8 }, { "kind": "wood", "x": 9, "z": 9 }]""",
        villagers: """[{ "x": 2, "z": 2 }, { "x": 10, "z": 10 }, { "x": 12, "z": 12 }]""");

    [Fact]
    public void CopiesToSeveralVillagersForFreeAndEachRunsItsOwn()
    {
        SimWorld world = World();
        Villager a = world.Villagers[0], b = world.Villagers[1], c = world.Villagers[2];
        Teach(world, a, Litany(Gather("wood", 4, 4), Put("wood", 4, 4)));
        Run(world, 40);
        world.Enqueue(new CopyLitanyCommand(a.Id, new[] { b.Id, c.Id }));
        world.Tick();
        Assert.Same(a.Litany, b.Litany);
        Assert.Same(a.Litany, c.Litany);
        Assert.All(world.LastCopyResults.Values, r => Assert.Equal(LitanyFit.Ok, r));
        Assert.Equal(0, b.CommandIndex); // começa do início, independente de onde o outro está
        Run(world, 100);
        // Os três colhem árvores diferentes (reserva) e entregam no mesmo baú.
        Assert.Equal(3, world.Villagers.Select(v => v.Target).Where(t => t is not null).Distinct().Count()
            + world.Villagers.Count(v => v.Target is null));
        Assert.True(world.BuildingAt(new GridPos(4, 4))!.Storage!.Count("wood") >= 2);
    }

    [Fact]
    public void AVillagerWithoutTheIntelligenceRefusesTheCopy()
    {
        SimWorld world = World();
        Villager smart = world.Villagers[0], plain = world.Villagers[1];
        smart.Intelligence = 2;
        Teach(world, smart, Litany(Enumerable.Repeat(GoTo(3, 3), 3).Concat(Enumerable.Repeat(GoTo(5, 5), 4)).ToArray()));
        world.Enqueue(new CopyLitanyCommand(smart.Id, new[] { plain.Id }));
        world.Tick();
        Assert.Equal(LitanyFit.TooLong, world.LastCopyResults[plain.Id]);
        Assert.Null(plain.Litany);
    }

    [Fact]
    public void CopyingFromAVillagerWithoutALitanyDoesNothing()
    {
        SimWorld world = World();
        world.Enqueue(new CopyLitanyCommand(world.Villagers[0].Id, new[] { world.Villagers[1].Id }));
        world.Tick();
        Assert.Empty(world.LastCopyResults);
        Assert.Null(world.Villagers[1].Litany);
    }
}
