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
            TestWorlds.DataFile("villagers.json"),
            TestWorlds.DataFile("buildings.json"),
            TestWorlds.DataFile("recipes.json"),
            TestWorlds.DataFile("terrain.json"));
        SimWorld world = MapLoader.Parse(TestWorlds.DataFile("maps/mapa_teste.json"), data);

        Assert.Contains("wood", data.Resources.Keys);
        Assert.Equal("mana_tower", data.Buildings[0].Kind); // a torre é a tecla 1 (sem esteiras desde 30/09)
        Assert.DoesNotContain(data.Buildings, b => b.Kind is "belt" or "moth");
        Assert.NotEmpty(world.Resources);
        Assert.False(world.IsSolid(new GridPos((int)world.Castellan.Position.X, (int)world.Castellan.Position.Y)));
        Assert.Equal("grass", data.Terrains[0].Kind); // o primeiro terreno é o padrão
        Assert.Equal(data.Terrain("dirt").Index, world.Grid.TerrainAt(new GridPos(15, 16))); // pátio da base
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
        Assert.Throws<FormatException>(() => GameData.Parse(TestWorlds.Items, TestWorlds.Resources, TestWorlds.CastellanStats, TestWorlds.VillagerStats,
            """{ "chest": { "name": "Baú", "cost": { "gold": 1 }, "solid": true } }""", "{}"));
    }

    [Theory]
    [InlineData("""{ "x": { "machine": "castle", "inputs": { "wood": 1 }, "outputs": { "shaft": 1 }, "seconds": 1 } }""")]
    [InlineData("""{ "x": { "machine": "sawmill", "inputs": { "gold": 1 }, "outputs": { "shaft": 1 }, "seconds": 1 } }""")]
    [InlineData("""{ "x": { "machine": "sawmill", "inputs": { "wood": 1 }, "outputs": { "shaft": 1 }, "seconds": 0 } }""")]
    public void InvalidRecipesAreRejected(string recipes)
    {
        Assert.Throws<FormatException>(() => GameData.Parse(TestWorlds.Items, TestWorlds.Resources,
            TestWorlds.CastellanStats, TestWorlds.VillagerStats, TestWorlds.Buildings, recipes));
    }

    [Fact]
    public void OutOfBoundsCellIsRejected()
    {
        Assert.Throws<FormatException>(() =>
            TestWorlds.Open(resources: """[{ "kind": "wood", "x": 50, "z": 5 }]"""));
    }
}
