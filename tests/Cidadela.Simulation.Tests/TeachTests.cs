using System;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Ensinar por demonstração (docs/ladainhas.md): o que a protagonista faz vira a ladainha do aldeão.</summary>
public class TeachTests
{
    private static int Seconds(float s) => (int)MathF.Round(s * SimClock.TicksPerSecond);

    /// <summary>Ela em (5, 5); árvore (6, 6); baú (8, 5); Purificador com mana (5, 8); aldeão em (12, 12).</summary>
    private static SimWorld World() => MapLoader.Parse("""
        { "width": 20, "height": 20, "castellan": { "x": 5, "z": 5 },
          "resources": [{ "kind": "wood", "x": 6, "z": 6 }, { "kind": "wood", "x": 3, "z": 3 }],
          "buildings": [{ "kind": "chest", "x": 8, "z": 5 }, { "kind": "mana_tower", "x": 7, "z": 9 },
                        { "kind": "reliquary", "x": 8, "z": 10, "items": { "pure_shard": 5 } }, { "kind": "purifier", "x": 5, "z": 8 }],
          "villagers": [{ "x": 12, "z": 12 }] }
        """, TestWorlds.RealData());

    [Fact]
    public void GatheringAndPuttingBecomeALitanyThatTheVillagerRepeats()
    {
        SimWorld world = World();
        Villager v = world.Villagers[0];
        world.Enqueue(new StartTeachingCommand(v.Id));
        world.Enqueue(new GatherCommand(new GridPos(6, 6)));
        TestWorlds.Run(world, Seconds(4.5f)); // 2 toras
        world.Enqueue(new InsertItemCommand(new GridPos(8, 5), "wood"));
        world.Enqueue(new InsertItemCommand(new GridPos(8, 5), "wood")); // o mesmo "pôr" duas vezes vira um comando
        world.Enqueue(new FinishTeachingCommand());
        world.Tick();

        Assert.Null(world.Teaching);
        Assert.Equal(LitanyFit.Ok, world.LastTeachResult);
        Assert.NotNull(v.Litany);
        Assert.Equal(2, v.Litany!.Commands.Count);
        LitanyCommand gather = v.Litany.Commands[0], put = v.Litany.Commands[1];
        Assert.Equal(LitanyVerb.Gather, gather.Verb);
        Assert.Equal("wood", gather.Target!.Resource);
        Assert.Equal(new GridPos(6, 6), gather.Target.Cell); // em volta de onde ela colheu, não a árvore exata
        Assert.Equal(LitanyVerb.Put, put.Verb);
        Assert.Equal("wood", put.Item);
        Assert.Equal(new GridPos(8, 5), put.Target!.Cell);

        int before = world.BuildingAt(new GridPos(8, 5))!.Storage!.Count("wood");
        TestWorlds.Run(world, Seconds(40f));
        Assert.True(world.BuildingAt(new GridPos(8, 5))!.Storage!.Count("wood") > before, "o aldeão não repetiu a ladainha");
    }

    [Fact]
    public void TakingPuttingOperatingAndMarkingAPlaceAreRecorded()
    {
        SimWorld world = World();
        world.BuildingAt(new GridPos(8, 5))!.Storage!.Add("rotten_shard", 2);
        world.Enqueue(new StartTeachingCommand(world.Villagers[0].Id));
        world.Enqueue(new TakeAllCommand(new GridPos(8, 5)));
        world.Enqueue(new InsertItemCommand(new GridPos(5, 8), "rotten_shard"));
        world.Tick();
        world.Castellan.PlaceAt(new Vector2(5f, 7f));
        world.Enqueue(new OperatePostCommand());
        world.Enqueue(new MarkGoToCommand());
        world.Tick();

        var recorded = world.Teaching!.Commands;
        Assert.Equal(new[] { LitanyVerb.Take, LitanyVerb.Put, LitanyVerb.Operate, LitanyVerb.GoTo }, recorded.ConvertAll(c => c.Verb));
        Assert.Equal("rotten_shard", recorded[0].Item);
        Assert.Equal(new GridPos(5, 8), recorded[2].Target!.Cell);
        Assert.Equal(new GridPos(5, 7), recorded[3].Target!.Cell);
    }

    [Fact]
    public void ALitanyTooLongForTheIntelligenceIsRefusedAndKeepsRecording()
    {
        SimWorld world = World();
        Villager v = world.Villagers[0];
        world.Enqueue(new StartTeachingCommand(v.Id));
        for (int i = 0; i < 7; i++)
        {
            world.Castellan.PlaceAt(new Vector2(5f + (i % 2), 5f + i));
            world.Enqueue(new MarkGoToCommand());
            world.Tick();
        }
        world.Enqueue(new FinishTeachingCommand());
        world.Tick();
        Assert.Equal(LitanyFit.TooLong, world.LastTeachResult);
        Assert.Null(v.Litany);
        Assert.NotNull(world.Teaching); // continua gravando: dá para cancelar
        world.Enqueue(new CancelTeachingCommand());
        world.Tick();
        Assert.Null(world.Teaching);
        Assert.Null(v.Litany);
    }

    [Fact]
    public void WithoutRecordingNothingIsRecorded()
    {
        SimWorld world = World();
        world.Enqueue(new GatherCommand(new GridPos(6, 6)));
        TestWorlds.Run(world, 5);
        Assert.Null(world.Teaching);
        Assert.Null(world.Villagers[0].Litany);
    }
}
