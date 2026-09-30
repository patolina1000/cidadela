using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>O mapa da linha da flecha (data/maps/linha_flecha.json) de ponta a ponta: sem travar, flechas no arsenal.</summary>
public class ArrowLineMapTests
{
    private static SimWorld Map() => MapLoader.Parse(TestWorlds.DataFile("maps/linha_flecha.json"), TestWorlds.RealData());

    [Fact]
    public void EveryPostIsTakenAndAxleCranksNeedNobody()
    {
        SimWorld world = Map();
        TestWorlds.Run(world, 30 * SimClock.TicksPerSecond);
        foreach (Building b in world.Buildings.Where(b => b.Type.Posts is not null && !(b.Type.IsCrank && b.Turning)))
            Assert.True(b.CrewReady, $"{b.Kind} em ({b.Cell.X}, {b.Cell.Z}) sem equipe");
        Assert.Equal(4, world.Buildings.Count(b => b.Type.IsCrank && b.Turning));
        Assert.All(world.Buildings.Where(b => b.Type.IsCrank && b.Turning), b => Assert.All(b.Crew, Assert.Null));
        Assert.Equal(2, world.Villagers.Count(v => v.Home is null)); // 14 aldeões, 12 com trabalho
        Assert.All(world.Lines, l => Assert.True(l.Moving));
    }

    [Fact]
    public void TheLineMakesArrows()
    {
        SimWorld world = Map();
        TestWorlds.Run(world, 5 * 60 * SimClock.TicksPerSecond);
        Assert.True(world.BuildingAt(new GridPos(29, 12))!.Storage!.Count("arrow") >= 10);
    }
}
