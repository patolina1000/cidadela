using System;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class GameSpeedTests
{
    private static int TicksInOneSecond(SimClock clock)
    {
        int ticks = 0;
        for (int i = 0; i < 60; i++)
            ticks += clock.Advance(1.0 / 60.0);
        return ticks;
    }

    [Theory]
    [InlineData(1, 20)]
    [InlineData(2, 40)]
    [InlineData(3, 60)]
    public void SpeedMultipliesTicksPerRealSecond(int speed, int expected)
    {
        var clock = new SimClock { Speed = speed };
        Assert.InRange(TicksInOneSecond(clock), expected - 1, expected);
    }

    [Fact]
    public void PausedClockRunsNoTicksAndKeepsAlpha()
    {
        var clock = new SimClock();
        clock.Advance(0.025); // meio tick
        double alpha = clock.Alpha;
        clock.Paused = true;
        Assert.Equal(0, TicksInOneSecond(clock));
        Assert.Equal(alpha, clock.Alpha);
        clock.Paused = false;
        Assert.Equal(1, clock.Advance(0.025)); // retoma de onde parou
    }

    [Fact]
    public void LongFrameCapGrowsWithSpeed()
    {
        var clock = new SimClock { Speed = 3 };
        Assert.Equal(15, clock.Advance(1.0));
    }

    [Fact]
    public void SpeedBelowOneIsRejected()
    {
        var clock = new SimClock();
        Assert.Throws<ArgumentOutOfRangeException>(() => clock.Speed = 0);
    }

    [Fact]
    public void GameDataTimeFileHasOneTwoThree()
    {
        GameSpeeds speeds = GameSpeeds.Parse(TestWorlds.DataFile("time.json"));
        Assert.Equal(new[] { 1, 2, 3 }, speeds.Speeds);
    }

    [Theory]
    [InlineData("{ \"speeds\": [] }")]
    [InlineData("{ \"speeds\": [1, 0] }")]
    [InlineData("{ \"speeds\": [2, 1] }")]
    [InlineData("{ }")]
    public void InvalidTimeFileIsRejected(string json)
    {
        Assert.Throws<FormatException>(() => GameSpeeds.Parse(json));
    }
}
