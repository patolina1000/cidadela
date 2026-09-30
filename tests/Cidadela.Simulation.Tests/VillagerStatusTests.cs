using System;
using System.Collections.Generic;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class VillagerStatusTests
{
    // Mesmo mundo dos VillagerTests: cabana em (4, 4) com raio 8 e capacidade 3; aldeão carrega 2.
    private static SimWorld World(string resources, string villagers = """[{ "x": 2, "z": 2 }]""",
        string buildings = """[{ "kind": "lumber_hut", "x": 4, "z": 4, "direction": "east" }]""") =>
        TestWorlds.Open(x: 1, z: 18, resources: resources, buildings: buildings, villagers: villagers);

    [Fact]
    public void WithoutAHutItIsUnemployed()
    {
        SimWorld world = World("[]", buildings: "[]");
        TestWorlds.Run(world, 5);
        Assert.Equal(VillagerStatus.Unemployed, world.Villagers[0].Status);
    }

    [Fact]
    public void NothingInsideTheRadiusIsNoResource()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 18, "z": 18 }]""");
        TestWorlds.Run(world, 60);
        Assert.Equal(VillagerStatus.NoResource, world.Villagers[0].Status);
    }

    [Fact]
    public void AWalledOffResourceIsNoPath()
    {
        // Árvore em (8, 4) cercada de pedras nas 8 vizinhas: está no raio, mas não dá para encostar.
        var cells = new List<string> { """{ "kind": "wood", "x": 8, "z": 4 }""" };
        for (int dx = -1; dx <= 1; dx++)
        for (int dz = -1; dz <= 1; dz++)
            if (dx != 0 || dz != 0)
                cells.Add($$"""{ "kind": "stone", "x": {{8 + dx}}, "z": {{4 + dz}} }""");
        SimWorld world = World("[" + string.Join(",", cells) + "]");
        TestWorlds.Run(world, 60);
        Assert.Equal(VillagerStatus.NoPath, world.Villagers[0].Status);
    }

    [Fact]
    public void AFullHutIsHutFull()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        TestWorlds.Run(world, 1200);
        Assert.Equal(VillagerStatus.HutFull, world.Villagers[0].Status);
    }

    [Fact]
    public void WorkingGoesThroughGoingGatheringAndCarrying()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        var seen = new HashSet<VillagerStatus>();
        for (int i = 0; i < 200; i++)
        {
            world.Tick();
            seen.Add(world.Villagers[0].Status);
        }
        Assert.Contains(VillagerStatus.GoingToResource, seen);
        Assert.Contains(VillagerStatus.Gathering, seen);
        Assert.Contains(VillagerStatus.Carrying, seen);
        Assert.DoesNotContain(VillagerStatus.NoPath, seen);
        Assert.DoesNotContain(VillagerStatus.NoResource, seen);
    }

    [Fact]
    public void RestingWinsOverEverything()
    {
        SimWorld world = World("[]", buildings: "[]");
        world.Villagers[0].SetResting(true);
        Assert.Equal(VillagerStatus.Resting, world.Villagers[0].Status);
    }

    [Fact]
    public void DataFileHasEveryStatusAndTheProblemOnes()
    {
        VillagerStatusTable table = VillagerStatusTable.Parse(TestWorlds.DataFile("villager_status.json"));
        foreach (VillagerStatus status in VillagerStatuses.All)
            Assert.False(string.IsNullOrWhiteSpace(table[status].Text));
        Assert.True(table[VillagerStatus.Unemployed].Problem);
        Assert.True(table[VillagerStatus.HutFull].Problem);
        Assert.True(table[VillagerStatus.NoPath].Problem);
        Assert.True(table[VillagerStatus.NoResource].Problem);
        Assert.False(table[VillagerStatus.Gathering].Problem);
    }

    [Fact]
    public void AMissingStatusIsRejected()
    {
        Assert.Throws<FormatException>(() => VillagerStatusTable.Parse("""{ "sem_trabalho": { "text": "x", "icon": "dots" } }"""));
    }
}
