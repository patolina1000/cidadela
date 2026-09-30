using System;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Formas de bloqueio (polígono convexo da base e círculo do tronco) e o Castelão contornando as pedras reais.</summary>
public class ResourceShapeTests
{
    private static readonly ResourceShape Slab = new(Array.Empty<(Vector2, float)>(), ResourceShape.ConvexPolygon(new[]
        { new Vector2(-0.4f, -0.1f), new Vector2(0.4f, -0.1f), new Vector2(0.4f, 0.1f), new Vector2(-0.4f, 0.1f) }));

    [Fact]
    public void SignedDistanceIsNegativeInsideAndPositiveOutside()
    {
        Assert.Equal(-0.1f, Slab.SignedDistance(Vector2.Zero), 3);
        Assert.Equal(0.2f, Slab.SignedDistance(new Vector2(0f, 0.3f)), 3);
        Assert.Equal(0.1f, Slab.SignedDistance(new Vector2(0.5f, 0f)), 3);
    }

    [Fact]
    public void PlacedShapeTurnsWithTheModel()
    {
        // 90°: o eixo comprido (x) vira z, como o Basis(Up, yaw) da cena.
        ResourceShape turned = Slab.Placed(new Vector2(5f, 5f), MathF.PI / 2f, 1f);
        Assert.True(turned.SignedDistance(new Vector2(5f, 5.35f)) < 0f);
        Assert.True(turned.SignedDistance(new Vector2(5.35f, 5f)) > 0f);
    }

    [Fact]
    public void PushOutAtACornerGoesDiagonally()
    {
        Vector2 p = Slab.PushOut(new Vector2(0.45f, 0.15f), 0.3f);
        Assert.Equal(0.3f, Slab.SignedDistance(p), 3);
        Assert.True(p.X > 0.45f && p.Y > 0.15f);
    }

    private static GameData RealData() => GameData.Parse(
        TestWorlds.DataFile("items.json"), TestWorlds.DataFile("resources.json"), TestWorlds.DataFile("castellan.json"),
        TestWorlds.DataFile("villagers.json"), TestWorlds.DataFile("buildings.json"), TestWorlds.DataFile("recipes.json"),
        TestWorlds.DataFile("terrain.json"));

    private static SimWorld OneResource(string kind, int x, int z) => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 1, "z": 1 }, "resources": [{ "kind": "{{kind}}", "x": {{x}}, "z": {{z}} }] }
        """, RealData());

    [Theory]
    [InlineData("stone", 8, 8)]
    [InlineData("stone", 9, 8)]
    [InlineData("stone", 8, 9)]
    [InlineData("stone", 9, 9)]
    [InlineData("rotten_shard", 8, 8)]
    [InlineData("rotten_shard", 9, 8)]
    [InlineData("rotten_shard", 8, 9)]
    [InlineData("rotten_shard", 9, 9)]
    public void CastellanSlidesAroundRealStonesFromEveryDirection(string kind, int x, int z)
    {
        var center = new Vector2(x, z);
        for (int a = 0; a < 8; a++)
        {
            float angle = a * MathF.PI / 4f;
            var dir = new Vector2(MathF.Cos(angle), MathF.Sin(angle));
            var side = new Vector2(-dir.Y, dir.X);
            foreach (float offset in new[] { -0.2f, 0.2f })
            {
                SimWorld world = OneResource(kind, x, z);
                world.Castellan.PlaceAt(center - dir * 2f + side * offset);
                TestWorlds.Move(world, dir.X, dir.Y, ticks: 90); // 2,4 cél/s × 4,5 s: dá para passar a pedra
                Vector2 p = world.Castellan.Position;
                ResourceShape shape = world.ResourceAt(new GridPos(x, z))!.Shape!;
                Assert.True(shape.SignedDistance(p) >= world.Castellan.Stats.Radius - 0.01f, $"{kind} ({x},{z}) ângulo {a * 45}° desvio {offset}: dentro da pedra em {p}");
                Assert.True(Vector2.Dot(p - center, dir) > 1f, $"{kind} ({x},{z}) ângulo {a * 45}° desvio {offset}: enroscou em {p}");
            }
        }
    }

    [Theory]
    [InlineData("stone")]
    [InlineData("rotten_shard")]
    public void GatherReachIsMeasuredToTheRealBase(string kind)
    {
        SimWorld world = OneResource(kind, 5, 5);
        ResourceNode node = world.ResourceAt(new GridPos(5, 5))!;
        world.Castellan.PlaceAt(new Vector2(4f, 4f)); // diagonal colada
        Assert.True(world.Castellan.CanGather(node.Cell, node.Shape));
        world.Castellan.PlaceAt(new Vector2(3f, 5f)); // duas células
        Assert.False(world.Castellan.CanGather(node.Cell, node.Shape));
    }
}
