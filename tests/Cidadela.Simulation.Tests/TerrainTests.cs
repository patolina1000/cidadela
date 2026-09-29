using System;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class TerrainTests
{
    private const string Terrains = """
        { "grass": { "name": "Grama", "texture": "g.png" },
          "dirt":  { "name": "Terra", "texture": "d.png" },
          "sand":  { "name": "Areia", "texture": "s.png" } }
        """;

    private static GameData Data() => GameData.Parse(TestWorlds.Items, TestWorlds.Resources, TestWorlds.CastellanStats,
        TestWorlds.Buildings, TestWorlds.Recipes, Terrains);

    private static SimWorld Map(GameData data, string terrain) => MapLoader.Parse($$"""
        { "width": 12, "height": 12, "castellan": { "x": 10, "z": 10 }, "terrain": {{terrain}} }
        """, data);

    [Fact]
    public void WithoutTerrainTheWholeMapIsTheFirstType()
    {
        SimWorld world = TestWorlds.Open();
        Assert.Equal(0, world.Grid.TerrainAt(new GridPos(3, 4)));
        Assert.Equal("grass", world.Data.Terrains[0].Kind);
    }

    [Fact]
    public void PatchesPaintCirclesAndRectanglesAndTheLastOneWins()
    {
        GameData data = Data();
        SimWorld world = Map(data, """
            { "default": "grass", "patches": [
                { "kind": "dirt", "x": 5, "z": 5, "radius": 2 },
                { "kind": "sand", "x": 0, "z": 0, "width": 2, "height": 3 },
                { "kind": "sand", "x": 6, "z": 5, "width": 1, "height": 1 } ] }
            """);

        Assert.Equal(data.Terrain("dirt").Index, world.Grid.TerrainAt(new GridPos(5, 7)));  // na borda do círculo
        Assert.Equal(data.Terrain("grass").Index, world.Grid.TerrainAt(new GridPos(5, 8))); // fora
        Assert.Equal(data.Terrain("sand").Index, world.Grid.TerrainAt(new GridPos(1, 2)));  // no retângulo
        Assert.Equal(data.Terrain("grass").Index, world.Grid.TerrainAt(new GridPos(2, 2))); // fora
        Assert.Equal(data.Terrain("sand").Index, world.Grid.TerrainAt(new GridPos(6, 5)));  // por cima da terra
    }

    [Fact]
    public void DefaultCanBeAnyType()
    {
        GameData data = Data();
        SimWorld world = Map(data, """{ "default": "sand" }""");
        Assert.Equal(data.Terrain("sand").Index, world.Grid.TerrainAt(new GridPos(0, 0)));
    }

    [Fact]
    public void UnknownTerrainIsRejected()
    {
        Assert.Throws<FormatException>(() => Map(Data(), """{ "patches": [{ "kind": "lava", "x": 1, "z": 1, "radius": 1 }] }"""));
    }
}
