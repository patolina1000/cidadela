using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Carregador da linha 2 (dados do jogo): argila do Barreiro ao Oleiro e casca do Oleiro ao Cristal-mãe.</summary>
public class ClayCarrierTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    /// <summary>
    /// Água em x = 0, margem em x = 1. Barreiro (1, 6) com o operador em (2, 6); Oleiro (4, 6) com o operador em (4, 7);
    /// Cristal-mãe (7, 6); Posto de Carregadores (4, 3) com o carregador em (5, 3). Torres (3, 5) e (7, 4), Relicário em (3, 4).
    /// </summary>
    private static SimWorld World() => MapLoader.Parse("""
        { "width": 14, "height": 12, "castellan": { "x": 12, "z": 10 },
          "buildings": [{ "kind": "mana_tower", "x": 3, "z": 5 }, { "kind": "mana_tower", "x": 7, "z": 4 }, { "kind": "reliquary", "x": 3, "z": 4, "items": { "pure_shard": 12 } },
                        { "kind": "clay_pit", "x": 1, "z": 6 }, { "kind": "potter", "x": 4, "z": 6 },
                        { "kind": "carrier_post", "x": 4, "z": 3 }, { "kind": "mother_crystal", "x": 7, "z": 6 }],
          "villagers": [{ "x": 2, "z": 6 }, { "x": 4, "z": 7 }, { "x": 5, "z": 3 }],
          "terrain": { "default": "grass", "patches": [{ "kind": "water", "x": 0, "z": 0, "width": 1, "height": 12 },
                                                      { "kind": "bank", "x": 1, "z": 0, "width": 1, "height": 12 }] } }
        """, TestWorlds.RealData());

    [Fact]
    public void ClayGoesToThePotterAndTheShellToTheMotherCrystalOneAtATime()
    {
        SimWorld world = World();
        Building potter = world.BuildingAt(new GridPos(4, 6))!;
        potter.Machine!.Input.Add("water_jar", 2);
        Villager carrier = world.Villagers.Single(v => v.Home?.Kind == "carrier_post");
        int most = 0;
        for (int i = 0; i < Seconds(60f); i++)
        {
            world.Tick();
            most = System.Math.Max(most, carrier.CarryingCount);
        }
        Assert.Equal(1, most); // argila e casca são pesadas: 1 por viagem
        Assert.True(world.BuildingAt(new GridPos(7, 6))!.Machine!.Input.Count("shell") +
            world.BuildingAt(new GridPos(7, 6))!.VillagersFormed >= 1, "a casca não chegou ao Cristal-mãe");
        Assert.True(potter.Machine.Input.Count("clay") > 0 || potter.Machine.IsWorking);
    }
}
