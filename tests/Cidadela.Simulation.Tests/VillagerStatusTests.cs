using System;
using Xunit;
using static Cidadela.Simulation.Tests.TestWorlds;

namespace Cidadela.Simulation.Tests;

/// <summary>Estado do aldeão para o ícone (docs/ladainhas.md, "Estados visíveis"): sem ladainha, rezando, travado.</summary>
public class VillagerStatusTests
{
    private static SimWorld World() => Open(x: 1, z: 18, buildings: """[{ "kind": "chest", "x": 4, "z": 4 }]""",
        villagers: """[{ "x": 2, "z": 2 }]""");

    [Fact]
    public void WithoutALitanyItIsNoLitany()
    {
        SimWorld world = World();
        Run(world, 5);
        Assert.Equal(VillagerStatus.NoLitany, world.Villagers[0].Status);
    }

    [Fact]
    public void WithALitanyItIsChanting()
    {
        SimWorld world = World();
        Teach(world, world.Villagers[0], Litany(GoTo(10, 10)));
        Run(world, 2);
        Assert.Equal(VillagerStatus.Chanting, world.Villagers[0].Status);
    }

    [Fact]
    public void AStuckCommandIsStuckWithItsReason()
    {
        SimWorld world = World();
        Teach(world, world.Villagers[0], Litany(Put("wood", 4, 4)));
        Run(world, 2);
        Assert.Equal(VillagerStatus.Stuck, world.Villagers[0].Status);
        Assert.Equal(LitanyStuck.HandsEmpty, world.Villagers[0].Stuck);
    }

    [Fact]
    public void RestingWinsOverEverything()
    {
        SimWorld world = World();
        world.Villagers[0].SetResting(true);
        Assert.Equal(VillagerStatus.Resting, world.Villagers[0].Status);
    }

    [Fact]
    public void DataFileHasEveryStatusAndOnlyStuckIsAProblem()
    {
        VillagerStatusTable table = VillagerStatusTable.Parse(DataFile("villager_status.json"));
        foreach (VillagerStatus status in VillagerStatuses.All)
            Assert.False(string.IsNullOrWhiteSpace(table[status].Text));
        Assert.True(table[VillagerStatus.Stuck].Problem);
        Assert.False(table[VillagerStatus.Chanting].Problem);
        Assert.False(table[VillagerStatus.NoLitany].Problem);
    }

    [Fact]
    public void AMissingStatusIsRejected()
    {
        Assert.Throws<FormatException>(() => VillagerStatusTable.Parse("""{ "travado": { "text": "x", "icon": "cross" } }"""));
    }
}
