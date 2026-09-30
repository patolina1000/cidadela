using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Linha 2 (docs/linha_aldeoes.md): argila e casca são pesadas; a margem é um terreno.</summary>
public class ClayAndShellTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    [Theory]
    [InlineData("clay")]
    [InlineData("shell")]
    public void BeltRefusesClayAndShell(string kind)
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4, data: TestWorlds.RealData(),
            buildings: """[{ "kind": "belt", "x": 6, "z": 4, "direction": "east" }]""");
        world.Castellan.Inventory.Add(kind, 2);
        world.Enqueue(new InsertItemCommand(new GridPos(6, 4), kind));
        world.Tick();
        Assert.Empty(world.BuildingAt(new GridPos(6, 4))!.Belt!.Items);
        Assert.Equal(2, world.Castellan.Inventory.Count(kind));
    }

    [Theory]
    [InlineData("clay")]
    [InlineData("shell")]
    public void MothRefusesClayAndShell(string kind)
    {
        SimWorld world = MapLoader.Parse($$"""
            { "width": 20, "height": 20, "castellan": { "x": 17, "z": 17 },
              "buildings": [{ "kind": "mana_tower", "x": 10, "z": 8 }, { "kind": "reliquary", "x": 9, "z": 7, "items": { "pure_shard": 5 } },
                            { "kind": "chest", "x": 8, "z": 9, "items": { "{{kind}}": 5 } }, { "kind": "moth", "x": 9, "z": 9, "direction": "east" },
                            { "kind": "chest", "x": 10, "z": 9 }] }
            """, TestWorlds.RealData());
        TestWorlds.Run(world, Seconds(5f));
        Assert.True(world.BuildingAt(new GridPos(10, 9))!.Storage!.IsEmpty);
    }

    [Fact]
    public void BankIsATerrainPaintedByTheMap()
    {
        SimWorld world = MapLoader.Parse("""
            { "width": 10, "height": 10, "castellan": { "x": 5, "z": 5 },
              "terrain": { "default": "grass", "patches": [{ "kind": "water", "x": 0, "z": 0, "width": 1, "height": 10 },
                                                          { "kind": "bank", "x": 1, "z": 2, "width": 1, "height": 3 }] } }
            """, TestWorlds.RealData());
        Assert.True(world.IsBank(new GridPos(1, 3)));
        Assert.False(world.IsBank(new GridPos(1, 6)));
        Assert.False(world.IsSolid(new GridPos(1, 3))); // margem é chão: dá para andar
    }
}
