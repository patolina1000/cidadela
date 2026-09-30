using Xunit;

namespace Cidadela.Simulation.Tests;

public class SimClockTests
{
    [Fact]
    public void OneSecondOfSmallFramesGivesTwentyTicks()
    {
        var clock = new SimClock();
        int ticks = 0;
        for (int i = 0; i < 60; i++)
            ticks += clock.Advance(1.0 / 60.0);
        Assert.InRange(ticks, 19, 20); // 60 × (1/60) pode arredondar para 19 + resto
    }

    [Fact]
    public void LongFrameIsCappedAndDropsTheBacklog()
    {
        var clock = new SimClock();
        Assert.Equal(5, clock.Advance(1.0));
        Assert.Equal(0.0, clock.Alpha);
    }

    [Fact]
    public void PausedClockRunsNoTicksAndKeepsAlpha()
    {
        var clock = new SimClock();
        clock.Advance(0.025); // meio tick
        double alpha = clock.Alpha;
        clock.Paused = true;
        for (int i = 0; i < 60; i++)
            Assert.Equal(0, clock.Advance(1.0 / 60.0));
        Assert.Equal(alpha, clock.Alpha);
        clock.Paused = false;
        Assert.Equal(1, clock.Advance(0.025)); // retoma de onde parou
    }

    [Fact]
    public void NegativeDeltaIsIgnored()
    {
        var clock = new SimClock();
        Assert.Equal(0, clock.Advance(-1.0));
    }
}
