using Xunit;

namespace Cidadela.Simulation.Tests;

public class StressWorldTests
{
    [Fact]
    public void CreatesTheRequestedCounts()
    {
        var world = new StressWorld(80, 80, 5000, 500, 10000);
        Assert.Equal(5000, world.EnemyCount);
        Assert.Equal(500, world.MachineCount);
        Assert.Equal(10000, world.ItemCount);
        Assert.Equal(50, world.Lanes.Length); // 5 × 10 blocos de 16×8
    }

    [Fact]
    public void EnemiesStayInsideTheFieldAndMove()
    {
        var world = new StressWorld(32, 32, 200, 20, 100);
        float before = world.EnemyX[0];
        for (int t = 0; t < 200; t++)
            world.Tick();
        for (int i = 0; i < world.EnemyCount; i++)
        {
            Assert.InRange(world.EnemyX[i], 0f, 32f);
            Assert.InRange(world.EnemyZ[i], 0f, 32f);
        }
        Assert.Equal(200, world.TickCount);
        Assert.NotEqual(before, world.EnemyX[0]);
    }

    [Fact]
    public void ItemsRideTheLanePerimeter()
    {
        var world = new StressWorld(32, 16, 0, 0, 40);
        for (int t = 0; t < 900; t++) // mais de uma volta (perímetro 40 células a 1,875/s)
        {
            world.Tick();
            for (int i = 0; i < world.ItemCount; i++)
            {
                var lane = world.Lanes[i % world.Lanes.Length];
                float x = world.ItemX[i] - 0.5f, z = world.ItemZ[i] - 0.5f;
                bool onVertical = (NearlyEqual(x, lane.X0) || NearlyEqual(x, lane.X0 + lane.W)) && z >= lane.Z0 - 1e-3f && z <= lane.Z0 + lane.H + 1e-3f;
                bool onHorizontal = (NearlyEqual(z, lane.Z0) || NearlyEqual(z, lane.Z0 + lane.H)) && x >= lane.X0 - 1e-3f && x <= lane.X0 + lane.W + 1e-3f;
                Assert.True(onVertical || onHorizontal, $"item {i} fora do circuito em ({x}, {z}) no tick {t}");
                // O passo entre o tick anterior e o atual nunca atravessa o retângulo.
                float dx = world.ItemX[i] - world.ItemPrevX[i], dz = world.ItemZ[i] - world.ItemPrevZ[i];
                Assert.True(dx * dx + dz * dz < 1f, $"item {i} pulou {dx}, {dz} no tick {t}");
            }
        }
    }

    [Fact]
    public void SameSeedGivesSamePositions()
    {
        var a = new StressWorld(40, 40, 300, 30, 300, seed: 7);
        var b = new StressWorld(40, 40, 300, 30, 300, seed: 7);
        for (int t = 0; t < 100; t++) { a.Tick(); b.Tick(); }
        Assert.Equal(a.EnemyX, b.EnemyX);
        Assert.Equal(a.ItemZ, b.ItemZ);
    }

    [Fact]
    public void LaneAndMachineCellsAreOccupied()
    {
        var world = new StressWorld(16, 8, 0, 10, 0);
        Assert.True(world.IsOccupied(new GridPos(1, 1)));   // canto do circuito
        Assert.True(world.IsOccupied(new GridPos(8, 1)));   // borda de cima
        Assert.False(world.IsOccupied(new GridPos(0, 0)));  // fora do circuito
        Assert.True(world.IsOccupied(new GridPos(3, 3)));   // primeira máquina
    }

    private static bool NearlyEqual(float a, float b) => System.MathF.Abs(a - b) < 1e-3f;
}
