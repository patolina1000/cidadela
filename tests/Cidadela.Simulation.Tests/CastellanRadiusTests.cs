using System;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Raio de colisão da protagonista em 50% (data/castellan.json, 0,15; decisão do Arthur, 29/09/2026), com os dados reais:
/// continua sem entrar em tronco, pedra, veio e construção; passa entre duas árvores mesmo fora do meio; coleta e alcance
/// iguais.
/// </summary>
public class CastellanRadiusTests
{
    private static GameData RealData() => GameData.Parse(
        TestWorlds.DataFile("items.json"), TestWorlds.DataFile("resources.json"), TestWorlds.DataFile("castellan.json"),
        TestWorlds.DataFile("villagers.json"), TestWorlds.DataFile("buildings.json"), TestWorlds.DataFile("recipes.json"),
        TestWorlds.DataFile("terrain.json"));

    private static SimWorld World(string resources = "[]", string buildings = "[]") => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 1, "z": 1 }, "resources": {{resources}}, "buildings": {{buildings}} }
        """, RealData());

    [Fact]
    public void TheRealRadiusIsHalfTheOldOne()
    {
        Assert.Equal(0.15f, RealData().Castellan.Radius, 3);
    }

    [Theory]
    [InlineData("wood")]
    [InlineData("stone")]
    [InlineData("rotten_shard")]
    public void SheStillNeverWalksIntoAResource(string kind)
    {
        for (int a = 0; a < 8; a++)
        {
            float angle = a * MathF.PI / 4f;
            var dir = new Vector2(MathF.Cos(angle), MathF.Sin(angle));
            SimWorld world = World($$"""[{ "kind": "{{kind}}", "x": 8, "z": 8 }]""");
            ResourceShape shape = world.ResourceAt(new GridPos(8, 8))!.Shape!;
            world.Castellan.PlaceAt(new Vector2(8f, 8f) - dir * 2f);
            world.Enqueue(new MoveCommand(dir));
            for (int i = 0; i < 90; i++)
            {
                world.Tick();
                Assert.True(shape.SignedDistance(world.Castellan.Position) >= 0.14f, $"{kind} {a * 45}°: entrou em {world.Castellan.Position}");
            }
        }
    }

    [Fact]
    public void SheStillStopsAtABuilding()
    {
        SimWorld world = World(buildings: """[{ "kind": "chest", "x": 8, "z": 8 }]""");
        world.Castellan.PlaceAt(new Vector2(8f, 11f));
        TestWorlds.Move(world, 0f, -1f, ticks: 60);
        // O baú ocupa a célula inteira (borda em z = 8,5): o corpo de 0,15 encosta em z = 8,65; contra parede o passo
        // inteiro é recusado quando bate (0,12 por tick), então para até um passo antes.
        Assert.InRange(world.Castellan.Position.Y, 8.64f, 8.78f);
    }

    [Theory]
    [InlineData(4.3f)]
    [InlineData(4.5f)]
    [InlineData(4.7f)]
    public void SheWalksBetweenTwoRealTreesEvenOffCentre(float x)
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 4, "z": 4 }, { "kind": "wood", "x": 5, "z": 4 }]""");
        world.Castellan.PlaceAt(new Vector2(x, 7f));
        TestWorlds.Move(world, 0f, -1f, ticks: 100); // 1,267 cél/s × 5 s
        Assert.True(world.Castellan.Position.Y < 2.5f, $"de x = {x}: parou em {world.Castellan.Position}");
    }

    [Fact]
    public void GatherAndBuildReachDoNotDependOnTheRadius()
    {
        SimWorld world = World("""[{ "kind": "wood", "x": 5, "z": 5 }, { "kind": "wood", "x": 7, "z": 5 }]""");
        world.Castellan.PlaceAt(new Vector2(4f, 4f));
        ResourceNode diagonal = world.ResourceAt(new GridPos(5, 5))!, far = world.ResourceAt(new GridPos(7, 5))!;
        Assert.True(world.Castellan.CanGather(diagonal.Cell, diagonal.Shape)); // diagonal colada, como antes
        Assert.False(world.Castellan.CanGather(far.Cell, far.Shape));          // três células, como antes
        Assert.Equal(10f, world.Castellan.Stats.Reach);
        Assert.Equal(1.3f, world.Castellan.Stats.GatherSurfaceReach, 3);
    }
}
