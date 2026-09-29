using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class CastellanMovementTests
{
    [Fact]
    public void WalksItsSpeedInOneSecond()
    {
        SimWorld world = TestWorlds.Open(x: 3, z: 3);
        TestWorlds.Move(world, 1f, 0f, ticks: 20);
        Assert.Equal(9f, world.Castellan.Position.X, 3);
        Assert.Equal(3f, world.Castellan.Position.Y, 3);
    }

    [Fact]
    public void SpeedMustBePositive()
    {
        Assert.Throws<System.FormatException>(() => GameData.Parse(TestWorlds.Items, TestWorlds.Resources,
            """{ "speed": 0.0 }""", TestWorlds.VillagerStats, TestWorlds.Buildings, TestWorlds.Recipes));
    }

    [Fact]
    public void DiagonalIsNotFaster()
    {
        SimWorld world = TestWorlds.Open(x: 3, z: 3);
        TestWorlds.Move(world, 1f, 1f, ticks: 20);
        float walked = Vector2.Distance(new Vector2(3f, 3f), world.Castellan.Position);
        Assert.Equal(6f, walked, 3);
    }

    [Fact]
    public void StaysInsideTheMap()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1);
        TestWorlds.Move(world, -1f, -1f, ticks: 100);
        Assert.Equal(Vector2.Zero, world.Castellan.Position);
    }

    [Fact]
    public void DoesNotWalkThroughAResource()
    {
        SimWorld world = TestWorlds.Open(x: 3, z: 3, resources: """[{ "kind": "wood", "x": 6, "z": 3 }]""");
        TestWorlds.Move(world, 1f, 0f, ticks: 100);
        // Borda do corpo (centro + 0,5 + raio) não passa da borda da célula 6.
        Assert.True(world.Castellan.Position.X + 0.5f + 0.3f <= 6f + 1e-4f);
        Assert.True(world.Castellan.Position.X > 4.5f);
    }

    [Fact]
    public void SlidesAlongAWallWhenMovingDiagonally()
    {
        SimWorld world = TestWorlds.Open(x: 3, z: 3, resources: """[{ "kind": "wood", "x": 6, "z": 3 }]""");
        TestWorlds.Move(world, 1f, 0f, ticks: 100); // encosta na árvore
        float xAtWall = world.Castellan.Position.X;
        TestWorlds.Move(world, 1f, 1f, ticks: 3);
        Assert.True(world.Castellan.Position.Y > 3.5f);
        Assert.True(world.Castellan.Position.X >= xAtWall);
    }

    [Fact]
    public void FacesWhereItWalks()
    {
        SimWorld world = TestWorlds.Open();
        TestWorlds.Move(world, -1f, 0f, ticks: 1);
        Assert.Equal(new Vector2(-1f, 0f), world.Castellan.Facing);
    }
}
