using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Linha 2 (docs/linha_aldeoes.md): argila e casca são pesadas; a margem é um terreno.</summary>
public class ClayAndShellTests
{
    [Theory]
    [InlineData("clay")]
    [InlineData("shell")]
    public void ClayAndShellAreHeavy(string kind) =>
        Assert.Equal(ItemWeight.Heavy, TestWorlds.RealData().Item(kind).Weight);

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
