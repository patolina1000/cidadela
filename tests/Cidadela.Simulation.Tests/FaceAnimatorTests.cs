using System;
using System.Collections.Generic;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class FaceAnimatorTests
{
    private const float Step = 0.005f;

    private static FaceTable Table() => FaceTable.Parse(TestWorlds.DataFile("villager_expressions.json"));

    /// <summary>Roda em passos de 5 ms e devolve cada piscar: quando começou, quando acabou e a sequência de quadros.</summary>
    private static List<(float startedAt, float endedAt, List<string> frames)> Blinks(FaceAnimator face, VillagerExpression expression, float seconds)
    {
        var blinks = new List<(float, float, List<string>)>();
        float t = 0f, startedAt = -1f;
        List<string> frames = new();
        for (int i = 0; i < seconds / Step; i++)
        {
            face.Advance(Step, expression);
            t += Step;
            if (face.Blinking)
            {
                if (startedAt < 0f)
                    startedAt = t;
                if (frames.Count == 0 || frames[^1] != face.Eyes)
                    frames.Add(face.Eyes);
            }
            else if (startedAt >= 0f)
            {
                blinks.Add((startedAt, t, frames));
                startedAt = -1f;
                frames = new List<string>();
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
    public void BlinkFramesComeFromTheJsonWithDefaults()
    {
        FaceTable fromFile = Table();
        Assert.Equal("meio_fechado", fromFile.HalfClosedEyes);
        Assert.Equal("fechado", fromFile.ClosedEyes);

        string custom = """
            { "piscar": { "meioFechado": "olhos_semi", "fechado": "olhos_fechados" },
              "expressoes": {
                "distraido": { "olhos": "a", "boca": "b" }, "esforco": { "olhos": "a", "boca": "b" },
                "feliz": { "olhos": "a", "boca": "b" }, "sonolento": { "olhos": "a", "boca": "b" },
                "dormindo": { "olhos": "a", "boca": "b" }, "espantado": { "olhos": "a", "boca": "b" },
                "preocupado": { "olhos": "a", "boca": "b" }, "chorando": { "olhos": "a", "boca": "b" },
                "bravo": { "olhos": "a", "boca": "b" } } }
            """;
        FaceTable table = FaceTable.Parse(custom);
        Assert.Equal("olhos_semi", table.HalfClosedEyes);
        Assert.Equal("olhos_fechados", table.ClosedEyes);
    }

    [Fact]
    public void MissingExpressionIsRejected()
    {
        Assert.Throws<FormatException>(() => FaceTable.Parse("""{ "expressoes": { "feliz": { "olhos": "a", "boca": "b" } } }"""));
    }

    [Fact]
    public void BlinksEveryTwoToSixSecondsForAboutFifteenHundredthsOfASecond()
    {
        var face = new FaceAnimator(7, Table());
        var blinks = Blinks(face, VillagerExpression.Distracted, 60f);
        Assert.InRange(blinks.Count, 60 / 6 - 1, 60 / 2 + 1);
        float last = 0f;
        foreach ((float startedAt, float endedAt, _) in blinks)
        {
            Assert.InRange(startedAt - last, FaceAnimator.MinBlinkInterval - 0.02f, FaceAnimator.MaxBlinkInterval + FaceAnimator.BlinkSeconds + 0.02f);
            Assert.InRange(endedAt - startedAt, FaceAnimator.BlinkSeconds - 0.01f, FaceAnimator.BlinkSeconds + 0.01f);
            last = startedAt;
        }
    }

    [Fact]
    public void ABlinkGoesHalfClosedThenClosedThenHalfClosed()
    {
        FaceTable table = Table();
        var blinks = Blinks(new FaceAnimator(7, table), VillagerExpression.Happy, 20f);
        Assert.NotEmpty(blinks);
        foreach ((_, _, List<string> frames) in blinks)
            Assert.Equal(new[] { table.HalfClosedEyes, table.ClosedEyes, table.HalfClosedEyes }, frames);
    }

    [Fact]
    public void EachBlinkPhaseLastsItsShare()
    {
        // 0,04 s meio fechado, 0,07 s fechado, 0,04 s meio fechado, medido em passos de 5 ms.
        var face = new FaceAnimator(7, Table());
        FaceTable table = Table();
        for (int i = 0; i < 4000 && !face.Blinking; i++)
            face.Advance(Step, VillagerExpression.Distracted);
        Assert.True(face.Blinking);
        float half1 = 0f, closed = 0f, half2 = 0f;
        while (face.Blinking && face.Eyes == table.HalfClosedEyes) { half1 += Step; face.Advance(Step, VillagerExpression.Distracted); }
        while (face.Blinking && face.Eyes == table.ClosedEyes) { closed += Step; face.Advance(Step, VillagerExpression.Distracted); }
        while (face.Blinking && face.Eyes == table.HalfClosedEyes) { half2 += Step; face.Advance(Step, VillagerExpression.Distracted); }
        Assert.False(face.Blinking);
        // Medido em passos discretos: cada fase pode variar um passo, mais a folga do ponto flutuante.
        const float slack = Step * 1.5f;
        Assert.InRange(half1, FaceAnimator.HalfClosedSeconds - slack, FaceAnimator.HalfClosedSeconds + slack);
        Assert.InRange(closed, FaceAnimator.ClosedSeconds - slack, FaceAnimator.ClosedSeconds + slack);
        Assert.InRange(half2, FaceAnimator.HalfClosedSeconds - slack, FaceAnimator.HalfClosedSeconds + slack);
    }

    [Fact]
    public void TheMouthKeepsTheExpressionAndTheEyesReturnToItAfterTheBlink()
    {
        var face = new FaceAnimator(3, Table());
        FaceTable table = Table();
        for (int i = 0; i < 2000; i++)
        {
            face.Advance(0.01f, VillagerExpression.Happy);
            Assert.Equal(table.For(VillagerExpression.Happy).Mouth, face.Mouth);
            if (!face.Blinking)
                Assert.Equal(table.For(VillagerExpression.Happy).Eyes, face.Eyes);
            else
                Assert.Contains(face.Eyes, new[] { table.HalfClosedEyes, table.ClosedEyes });
        }
    }

    [Fact]
    public void SameIdBlinksAtTheSameTimesAndDifferentIdsDiffer()
    {
        var a = Blinks(new FaceAnimator(11, Table()), VillagerExpression.Distracted, 30f);
        var b = Blinks(new FaceAnimator(11, Table()), VillagerExpression.Distracted, 30f);
        var c = Blinks(new FaceAnimator(12, Table()), VillagerExpression.Distracted, 30f);
        Assert.Equal(a.ConvertAll(x => (x.startedAt, x.endedAt)), b.ConvertAll(x => (x.startedAt, x.endedAt)));
        Assert.NotEqual(a.ConvertAll(x => (x.startedAt, x.endedAt)), c.ConvertAll(x => (x.startedAt, x.endedAt)));
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
        for (int i = 0; i < 4000 && !face.Blinking; i++)
            face.Advance(Step, VillagerExpression.Distracted);
        Assert.True(face.Blinking);
        face.Advance(Step, VillagerExpression.Sleepy);
        Assert.False(face.Blinking);
    }
}
