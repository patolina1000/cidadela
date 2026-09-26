using System.Collections.Generic;
using Xunit;

namespace Cidadela.Simulation.Tests;

public class GridPathTests
{
    private static bool Open(GridPos c) => c.X < 0 || c.Z < 0 || c.X >= 10 || c.Z >= 10;

    [Fact]
    public void StraightLineWhenNothingIsInTheWay()
    {
        List<GridPos>? path = GridPath.Find(Open, new GridPos(0, 0), new[] { new GridPos(3, 0) });
        Assert.Equal(new[] { new GridPos(1, 0), new GridPos(2, 0), new GridPos(3, 0) }, path);
    }

    [Fact]
    public void GoesAroundAWall()
    {
        // Parede em x = 2, de z = 0 a z = 3; o caminho precisa descer até z = 4 e voltar.
        var wall = new HashSet<GridPos> { new(2, 0), new(2, 1), new(2, 2), new(2, 3) };
        bool Solid(GridPos c) => Open(c) || wall.Contains(c);
        List<GridPos>? path = GridPath.Find(Solid, new GridPos(0, 0), new[] { new GridPos(4, 0) });
        Assert.NotNull(path);
        Assert.Equal(new GridPos(4, 0), path![^1]);
        Assert.DoesNotContain(path, wall.Contains);
        Assert.Contains(path, c => c.Z >= 4);
    }

    [Fact]
    public void DoesNotCutCornersDiagonally()
    {
        // Duas células sólidas se tocando pela quina: a diagonal entre elas é proibida.
        var solid = new HashSet<GridPos> { new(1, 0), new(0, 1) };
        List<GridPos>? path = GridPath.Find(c => Open(c) || solid.Contains(c), new GridPos(0, 0), new[] { new GridPos(1, 1) });
        Assert.Null(path);
    }

    [Fact]
    public void NullWhenUnreachableAndEmptyWhenAlreadyThere()
    {
        var box = new HashSet<GridPos> { new(4, 5), new(6, 5), new(5, 4), new(5, 6), new(4, 4), new(6, 6), new(4, 6), new(6, 4) };
        Assert.Null(GridPath.Find(c => Open(c) || box.Contains(c), new GridPos(0, 0), new[] { new GridPos(5, 5) }));
        Assert.Empty(GridPath.Find(Open, new GridPos(2, 2), new[] { new GridPos(2, 2) })!);
    }

    [Fact]
    public void PicksTheCloserOfSeveralGoals()
    {
        List<GridPos>? path = GridPath.Find(Open, new GridPos(0, 0), new[] { new GridPos(8, 8), new GridPos(2, 0) });
        Assert.Equal(new GridPos(2, 0), path![^1]);
    }
}
