using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Cabelo sorteado e expressão do rosto (GDD, tabela de expressões do aldeão).</summary>
public class VillagerLookTests
{
    private static SimWorld World(string resources = "[]", string villagers = """[{ "x": 2, "z": 2 }]""",
        string buildings = """[{ "kind": "lumber_hut", "x": 4, "z": 4, "direction": "east" }]""") =>
        TestWorlds.Open(x: 1, z: 18, resources: resources, buildings: buildings, villagers: villagers);

    [Fact]
    public void HairVariantIsBetweenOneAndFiveAndFixedByTheId()
    {
        string many = "[" + string.Join(",", Enumerable.Range(0, 12).Select(i => $$"""{ "x": {{2 + i}}, "z": 10 }""")) + "]";
        SimWorld a = World(villagers: many, buildings: "[]");
        SimWorld b = World(villagers: many, buildings: "[]");
        var seen = new System.Collections.Generic.HashSet<int>();
        for (int i = 0; i < a.Villagers.Count; i++)
        {
            Assert.InRange(a.Villagers[i].HairVariant, 1, Villager.HairVariants);
            Assert.Equal(a.Villagers[i].HairVariant, b.Villagers[i].HairVariant);
            seen.Add(a.Villagers[i].HairVariant);
        }
        Assert.True(seen.Count >= 3, "12 aldeões deviam ter pelo menos 3 cabelos diferentes");
    }

    [Fact]
    public void StartsDistracted()
    {
        SimWorld world = World(buildings: "[]");
        world.Tick();
        Assert.Equal(VillagerExpression.Distracted, world.Villagers[0].Expression);
    }

    [Fact]
    public void EffortWhileGatheringOrCarrying()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        bool sawEffort = false;
        for (int i = 0; i < 200 && !sawEffort; i++)
        {
            world.Tick();
            Villager v = world.Villagers[0];
            if (v.Task == VillagerTask.Gathering || v.CarryingCount > 0)
            {
                Assert.Equal(VillagerExpression.Effort, v.Expression);
                sawEffort = true;
            }
        }
        Assert.True(sawEffort);
    }

    [Fact]
    public void HappyRightAfterDeliveringThenBackToWork()
    {
        // Árvore longe (8 células): a próxima entrega demora mais que a alegria dura.
        SimWorld world = World("""[{ "kind": "wood", "x": 12, "z": 4 }]""");
        Workplace hut = world.BuildingAt(new GridPos(4, 4))!.Workplace!;
        int before = hut.Stored.Count("wood");
        int deliveredAt = -1;
        for (int i = 0; i < 400; i++)
        {
            world.Tick();
            if (hut.Stored.Count("wood") > before) { deliveredAt = i; break; }
        }
        Assert.True(deliveredAt >= 0, "nenhuma entrega em 400 ticks");
        Assert.Equal(VillagerExpression.Happy, world.Villagers[0].Expression);
        TestWorlds.Run(world, Villager.HappyTicks + 1);
        Assert.NotEqual(VillagerExpression.Happy, world.Villagers[0].Expression);
    }

    [Fact]
    public void SleepyAfterALongIdleAndSleepingWhenResting()
    {
        SimWorld world = World(buildings: "[]"); // sem cabana: ocioso
        TestWorlds.Run(world, Villager.SleepyAfterTicks - 1);
        Assert.Equal(VillagerExpression.Distracted, world.Villagers[0].Expression);
        world.Tick();
        Assert.Equal(VillagerExpression.Sleepy, world.Villagers[0].Expression);

        world.Villagers[0].SetResting(true);
        world.Tick();
        Assert.Equal(VillagerExpression.Sleeping, world.Villagers[0].Expression);
        world.Villagers[0].SetResting(false);
        world.Tick();
        Assert.Equal(VillagerExpression.Sleepy, world.Villagers[0].Expression);
    }

    [Fact]
    public void WorriedWhenTheHutIsFull()
    {
        // Cabana de teste guarda 3; com 6 madeiras perto, enche e o aldeão fica esperando.
        SimWorld world = World("""[{ "kind": "wood", "x": 7, "z": 4 }]""");
        Workplace hut = world.BuildingAt(new GridPos(4, 4))!.Workplace!;
        bool sawWorried = false;
        for (int i = 0; i < 1500 && !sawWorried; i++)
        {
            world.Tick();
            if (hut.Free <= 0 && world.Villagers[0].Task == VillagerTask.Waiting)
            {
                TestWorlds.Run(world, 2);
                sawWorried = world.Villagers[0].Expression == VillagerExpression.Worried;
            }
        }
        Assert.True(sawWorried, "o aldeão devia ficar preocupado com a cabana cheia");
    }
}
