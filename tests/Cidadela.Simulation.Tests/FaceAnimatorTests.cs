using System;
using System.Collections.Generic;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class FaceAnimatorTests
{
    private static FaceTable Table() => FaceTable.Parse(TestWorlds.DataFile("villager_expressions.json"));

    /// <summary>Roda em passos de 10 ms e devolve os instantes em que os olhos fecharam e reabriram.</summary>
    private static List<(float closedAt, float openedAt)> Blinks(FaceAnimator face, VillagerExpression expression, float seconds)
    {
        var blinks = new List<(float, float)>();
        const float dt = 0.01f;
        float t = 0f, closedAt = -1f;
        for (int i = 0; i < seconds / dt; i++)
        {
            face.Advance(dt, expression);
            t += dt;
            if (face.Blinking && closedAt < 0f)
                closedAt = t;
            else if (!face.Blinking && closedAt >= 0f)
            {
                blinks.Add((closedAt, t));
                closedAt = -1f;
            }
        }
        return blinks;
    }

    [Fact]
    public void TableCoversTheNineExpressionsOfTheGdd()
    {
        FaceTable table = Table();
        foreach (VillagerExpression e in VillagerExpressions.All)
        {
            (string eyes, string mouth) = table.For(e);
            Assert.False(string.IsNullOrEmpty(eyes));
            Assert.False(string.IsNullOrEmpty(mouth));
        }
        Assert.Equal(("fechado", "entreaberta"), table.For(VillagerExpression.Sleeping));
    }

    [Fact]
    public void MissingExpressionIsRejected()
    {
        Assert.Throws<FormatException>(() => FaceTable.Parse("""{ "expressoes": { "feliz": { "olhos": "a", "boca": "b" } } }"""));
    }

    [Fact]
    public void BlinksEveryTwoToSixSecondsForAboutATenthOfASecond()
    {
        var face = new FaceAnimator(7, Table());
        List<(float closedAt, float openedAt)> blinks = Blinks(face, VillagerExpression.Distracted, 60f);
        Assert.InRange(blinks.Count, 60 / 6 - 1, 60 / 2 + 1);
        float last = 0f;
        foreach ((float closedAt, float openedAt) in blinks)
        {
            Assert.InRange(closedAt - last, FaceAnimator.MinBlinkInterval - 0.02f, FaceAnimator.MaxBlinkInterval + FaceAnimator.ClosedSeconds + 0.02f);
            Assert.InRange(openedAt - closedAt, FaceAnimator.ClosedSeconds - 0.02f, FaceAnimator.ClosedSeconds + 0.02f);
            last = closedAt;
        }
    }

    [Fact]
    public void ClosedEyesUseTheClosedFrameAndTheMouthKeepsTheExpression()
    {
        var face = new FaceAnimator(3, Table());
        FaceTable table = Table();
        for (int i = 0; i < 1000; i++)
        {
            face.Advance(0.01f, VillagerExpression.Happy);
            Assert.Equal(table.For(VillagerExpression.Happy).Mouth, face.Mouth);
            Assert.Equal(face.Blinking ? table.ClosedEyes : table.For(VillagerExpression.Happy).Eyes, face.Eyes);
        }
    }

    [Fact]
    public void SameIdBlinksAtTheSameTimesAndDifferentIdsDiffer()
    {
        var a = Blinks(new FaceAnimator(11, Table()), VillagerExpression.Distracted, 30f);
        var b = Blinks(new FaceAnimator(11, Table()), VillagerExpression.Distracted, 30f);
        var c = Blinks(new FaceAnimator(12, Table()), VillagerExpression.Distracted, 30f);
        Assert.Equal(a, b);
        Assert.NotEqual(a, c);
    }

    [Theory]
    [InlineData(VillagerExpression.Sleeping)]
    [InlineData(VillagerExpression.Sleepy)]
    public void DoesNotBlinkWhenSleepingOrSleepy(VillagerExpression expression)
    {
        var face = new FaceAnimator(5, Table());
        Assert.Empty(Blinks(face, expression, 30f));
        Assert.Equal(Table().For(expression).Eyes, face.Eyes);
    }

    [Fact]
    public void ABlinkInterruptedBySleepEndsAtOnce()
    {
        var face = new FaceAnimator(9, Table());
        for (int i = 0; i < 2000 && !face.Blinking; i++)
            face.Advance(0.01f, VillagerExpression.Distracted);
        Assert.True(face.Blinking);
        face.Advance(0.01f, VillagerExpression.Sleepy);
        Assert.False(face.Blinking);
    }
}
