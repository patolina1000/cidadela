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
            TestWorlds.DataFile("castellan.json"),
            TestWorlds.DataFile("buildings.json"));
        SimWorld world = MapLoader.Parse(TestWorlds.DataFile("maps/mapa_teste.json"), data);

        Assert.Contains("wood", data.Resources.Keys);
        Assert.Equal("belt", data.Buildings[0].Kind); // a esteira é a tecla 1
        Assert.NotEmpty(world.Resources);
        Assert.NotEmpty(world.Buildings);
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
    public void UnknownBuildingKindIsRejected()
    {
        Assert.Throws<FormatException>(() =>
            TestWorlds.Open(buildings: """[{ "kind": "castle", "x": 5, "z": 5 }]"""));
    }

    [Fact]
    public void BuildingCostMustUseKnownResources()
    {
        Assert.Throws<FormatException>(() => GameData.Parse(TestWorlds.Resources, TestWorlds.CastellanStats,
            """{ "belt": { "name": "Esteira", "cost": { "gold": 1 }, "solid": false } }"""));
    }

    [Fact]
    public void OutOfBoundsCellIsRejected()
    {
        Assert.Throws<FormatException>(() =>
            TestWorlds.Open(resources: """[{ "kind": "wood", "x": 50, "z": 5 }]"""));
    }
}
