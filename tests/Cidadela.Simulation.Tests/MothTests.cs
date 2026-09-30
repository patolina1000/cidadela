using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Mariposas (docs/linha_energia.md) com os números do jogo: só leves, 1,2 s por item, sem mana pousam.</summary>
public class MothTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    private static string At(string kind, int x, int z, string extra = "") =>
        $$"""{ "kind": "{{kind}}", "x": {{x}}, "z": {{z}}{{extra}} }""";

    private static string Items(string kind, int n) => $$""", "items": { "{{kind}}": {{n}} }""";

    /// <summary>Torre em (10, 8) (área x 8–12, z 6–10) com um Relicário cheio em (9, 7), e as construções dadas.</summary>
    private static SimWorld World(string buildings) => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 17, "z": 17 },
          "buildings": [{{At("mana_tower", 10, 8)}}, {{At("reliquary", 9, 7, Items("pure_shard", 5))}}, {{buildings}}] }
        """, TestWorlds.RealData());

    private static Inventory Chest(SimWorld world, int x, int z) => world.BuildingAt(new GridPos(x, z))!.Storage!;

    [Fact]
    public void RefusesHeavyItems()
    {
        SimWorld world = World($"{At("chest", 8, 9, Items("rotten_shard", 5))}, {At("moth", 9, 9, ", \"direction\": \"east\"")}, {At("chest", 10, 9)}");
        TestWorlds.Run(world, Seconds(5f));
        Assert.True(Chest(world, 10, 9).IsEmpty);
        Assert.Null(world.BuildingAt(new GridPos(9, 9))!.Moth!.Carrying);
    }

    [Fact]
    public void CarriesOneLightItemEvery1Point2Seconds()
    {
        SimWorld world = World($"{At("chest", 8, 9, Items("pure_shard", 10))}, {At("moth", 9, 9, ", \"direction\": \"east\"")}, {At("chest", 10, 9)}");
        TestWorlds.Run(world, Seconds(6f) + 2);
        Assert.Equal(5, Chest(world, 10, 9).Count("pure_shard"));
        TestWorlds.Run(world, Seconds(6f));
        Assert.Equal(10, Chest(world, 10, 9).Count("pure_shard"));
    }

    [Fact]
    public void ChestToBeltToMachineThroughTwoMoths()
    {
        // Baú → mariposa → 2 esteiras → mariposa → Purificador (a entrada aceita 2 jarros).
        SimWorld world = World($"{At("chest", 8, 9, Items("water_jar", 5))}, {At("moth", 9, 9, ", \"direction\": \"east\"")}, " +
            $"{At("belt", 10, 9, ", \"direction\": \"east\"")}, {At("belt", 11, 9, ", \"direction\": \"east\"")}, " +
            $"{At("moth", 12, 9, ", \"direction\": \"east\"")}, {At("purifier", 13, 9)}");
        TestWorlds.Run(world, Seconds(15f));
        Assert.Equal(2, world.BuildingAt(new GridPos(13, 9))!.Machine!.Input.Count("water_jar"));
    }

    [Fact]
    public void TakesTheOutputOfAMachine()
    {
        SimWorld world = World($"{At("purifier", 8, 9)}, {At("moth", 9, 9, ", \"direction\": \"east\"")}, {At("chest", 10, 9)}");
        world.BuildingAt(new GridPos(8, 9))!.Machine!.Output.Add("pure_shard", 2);
        TestWorlds.Run(world, Seconds(3f));
        Assert.Equal(2, Chest(world, 10, 9).Count("pure_shard"));
    }

    [Fact]
    public void WithoutManaItLands()
    {
        SimWorld world = World($"{At("chest", 2, 2, Items("pure_shard", 5))}, {At("moth", 3, 2, ", \"direction\": \"east\"")}, {At("chest", 4, 2)}");
        TestWorlds.Run(world, Seconds(5f));
        Assert.True(Chest(world, 4, 2).IsEmpty);
        Assert.True(world.BuildingAt(new GridPos(3, 2))!.Moth!.Landed);
    }

    [Fact]
    public void UsesMoreManaFlyingThanWaiting()
    {
        SimWorld idle = World($"{At("chest", 8, 9)}, {At("moth", 9, 9, ", \"direction\": \"east\"")}, {At("chest", 10, 9)}");
        TestWorlds.Run(idle, 5);
        Assert.Equal(0.1f, idle.ManaNetworks.Single().Demand, 3);

        SimWorld flying = World($"{At("chest", 8, 9, Items("pure_shard", 5))}, {At("moth", 9, 9, ", \"direction\": \"east\"")}, {At("chest", 10, 9)}");
        TestWorlds.Run(flying, 5);
        Assert.True(flying.BuildingAt(new GridPos(9, 9))!.Moth!.Flying);
        Assert.Equal(0.5f, flying.ManaNetworks.Single().Demand, 3);
    }
}
