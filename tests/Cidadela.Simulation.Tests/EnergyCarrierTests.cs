using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Carregador da linha da energia (números do jogo): o podre da Mina ao Purificador, 1 por viagem.</summary>
public class EnergyCarrierTests
{
    [Fact]
    public void ACarrierTakesRottenShardsFromTheMineToThePurifierOneAtATime()
    {
        // Mina no veio (10, 4) com o minerador em (11, 4); Purificador em (10, 8) com o operador em (10, 9) (sem água não
        // começa: a entrada só enche); Posto de Carregadores em (13, 6) com o carregador em (13, 7). Torre (10, 6) e Relicário cheio (9, 5) dão mana à mina.
        SimWorld world = MapLoader.Parse("""
            { "width": 20, "height": 20, "castellan": { "x": 17, "z": 17 },
              "resources": [{ "kind": "rotten_shard", "x": 10, "z": 4 }],
              "buildings": [{ "kind": "mana_tower", "x": 10, "z": 6 }, { "kind": "reliquary", "x": 9, "z": 5, "items": { "pure_shard": 5 } },
                            { "kind": "crystal_mine", "x": 10, "z": 4 }, { "kind": "purifier", "x": 10, "z": 8 },
                            { "kind": "carrier_post", "x": 13, "z": 6 }],
              "villagers": [{ "x": 11, "z": 4 }, { "x": 10, "z": 9 }, { "x": 13, "z": 7 }] }
            """, TestWorlds.RealData());
        Villager carrier = world.Villagers.Single(v => v.Home?.Kind == "carrier_post");
        int most = 0;
        for (int i = 0; i < 40 * SimClock.TicksPerSecond; i++)
        {
            world.Tick();
            most = System.Math.Max(most, carrier.CarryingCount);
        }
        Assert.Equal(1, most); // pesado: 1 por viagem
        Assert.Equal(4, world.BuildingAt(new GridPos(10, 8))!.Machine!.Input.Count("rotten_shard")); // encheu (2 ciclos)
    }
}
