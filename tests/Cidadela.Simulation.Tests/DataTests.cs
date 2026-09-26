using System;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class DataTests
{
    [Fact]
    public void RealDataFilesLoad()
    {
        GameData data = GameData.Parse(
            TestWorlds.DataFile("items.json"),
            TestWorlds.DataFile("resources.json"),
            TestWorlds.DataFile("castellan.json"),
            TestWorlds.DataFile("buildings.json"),
            TestWorlds.DataFile("recipes.json"));
        SimWorld world = MapLoader.Parse(TestWorlds.DataFile("maps/mapa_teste.json"), data);

        Assert.Contains("wood", data.Resources.Keys);
        Assert.Equal("belt", data.Buildings[0].Kind); // a esteira é a tecla 1
        Assert.NotEmpty(world.Resources);
        Assert.NotEmpty(world.Buildings);
        Assert.NotNull(data.RecipeFor("sawmill"));
        Assert.Contains(world.Buildings, b => b.Machine is not null); // máquinas do mapa já trabalham
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
        Assert.Throws<FormatException>(() => GameData.Parse(TestWorlds.Items, TestWorlds.Resources, TestWorlds.CastellanStats,
            """{ "belt": { "name": "Esteira", "cost": { "gold": 1 }, "solid": false } }""", "{}"));
    }

    [Theory]
    [InlineData("""{ "x": { "machine": "castle", "inputs": { "wood": 1 }, "outputs": { "shaft": 1 }, "seconds": 1 } }""")]
    [InlineData("""{ "x": { "machine": "sawmill", "inputs": { "gold": 1 }, "outputs": { "shaft": 1 }, "seconds": 1 } }""")]
    [InlineData("""{ "x": { "machine": "sawmill", "inputs": { "wood": 1 }, "outputs": { "shaft": 1 }, "seconds": 0 } }""")]
    public void InvalidRecipesAreRejected(string recipes)
    {
        Assert.Throws<FormatException>(() => GameData.Parse(TestWorlds.Items, TestWorlds.Resources,
            TestWorlds.CastellanStats, TestWorlds.Buildings, recipes));
    }

    [Fact]
    public void OutOfBoundsCellIsRejected()
    {
        Assert.Throws<FormatException>(() =>
            TestWorlds.Open(resources: """[{ "kind": "wood", "x": 50, "z": 5 }]"""));
    }
}
