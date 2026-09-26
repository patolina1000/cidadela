using System;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class DataTests
{
    [Fact]
    public void RealDataFilesLoad()
    {
        GameData data = GameData.Parse(
            TestWorlds.DataFile("resources.json"),
            TestWorlds.DataFile("castellan.json"));
        SimWorld world = MapLoader.Parse(TestWorlds.DataFile("maps/mapa_teste.json"), data);

        Assert.Contains("wood", data.Resources.Keys);
        Assert.NotEmpty(world.Resources);
        Assert.False(world.IsSolid(new GridPos((int)world.Castellan.Position.X, (int)world.Castellan.Position.Y)));
    }

    [Fact]
    public void GatherSecondsBecomeTicks()
    {
        ResourceType stone = TestWorlds.Data().Resource("stone");
        Assert.Equal(30, stone.GatherTicks);
    }

    [Fact]
    public void UnknownResourceKindIsRejected()
    {
        Assert.Throws<FormatException>(() =>
            TestWorlds.Open(resources: """[{ "kind": "gold", "x": 5, "z": 5 }]"""));
    }

    [Fact]
    public void OutOfBoundsCellIsRejected()
    {
        Assert.Throws<FormatException>(() =>
            TestWorlds.Open(resources: """[{ "kind": "wood", "x": 50, "z": 5 }]"""));
    }
}
