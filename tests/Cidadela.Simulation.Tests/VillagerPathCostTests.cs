using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using Xunit;
using Xunit.Abstractions;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Custo do caminho dos aldeões por tick: 100 lenhadores trabalhando num bosque denso (60×60, ~30 % de árvores com
/// tronco). Mede a média de tempo de <see cref="SimWorld.Tick"/> e imprime no resultado do teste; o limite só pega
/// regressão grosseira.
/// </summary>
public class VillagerPathCostTests
{
    private readonly ITestOutputHelper _output;

    public VillagerPathCostTests(ITestOutputHelper output) => _output = output;

    internal static SimWorld Forest(int huts)
    {
        var rng = new Random(42);
        var resources = new List<string>();
        var buildings = new List<string>();
        var villagers = new List<string>();
        var taken = new HashSet<(int, int)>();
        for (int i = 0; i < huts; i++)
        {
            int x = 3 + (i % 10) * 5, z = 3 + (i / 10) * 5;
            taken.Add((x, z));
            buildings.Add($$"""{ "kind": "lumber_hut", "x": {{x}}, "z": {{z}} }""");
            villagers.Add($$"""{ "x": {{x + 1}}, "z": {{z + 1}} }""");
            taken.Add((x + 1, z + 1));
        }
        for (int x = 0; x < 60; x++)
        for (int z = 0; z < 60; z++)
            if (!taken.Contains((x, z)) && rng.NextDouble() < 0.3)
                resources.Add($$"""{ "kind": "wood", "x": {{x}}, "z": {{z}} }""");
        return MapLoader.Parse($$"""
            { "width": 60, "height": 60, "castellan": { "x": 58, "z": 58 },
              "resources": [{{string.Join(",", resources)}}], "buildings": [{{string.Join(",", buildings)}}],
              "villagers": [{{string.Join(",", villagers)}}] }
            """, ForestData());
    }

    // Cabanas que não enchem: os aldeões trabalham (e planejam caminhos) o tempo todo.
    private static GameData ForestData() => GameData.Parse(TestWorlds.Items,
        TestWorlds.Resources.Replace("\"amount\": 30 }", "\"amount\": 30, \"trunkRadius\": 0.2 }"),
        TestWorlds.CastellanStats, TestWorlds.VillagerStats,
        TestWorlds.Buildings.Replace("\"capacity\": 3", "\"capacity\": 100000"), TestWorlds.Recipes);


    [Fact]
    public void HundredVillagersInADenseForestStayCheapPerTick()
    {
        SimWorld world = Forest(100);
        TestWorlds.Run(world, 50); // aquece o JIT e o primeiro planejamento
        var watch = Stopwatch.StartNew();
        const int ticks = 600;
        TestWorlds.Run(world, ticks);
        double msPerTick = watch.Elapsed.TotalMilliseconds / ticks;
        int stored = 0;
        foreach (Building b in world.Buildings)
            stored += b.Workplace?.Stored.Count("wood") ?? 0;
        _output.WriteLine($"100 aldeões, bosque 60×60: {msPerTick:0.000} ms por tick; {stored} madeiras entregues em {ticks} ticks");
        Assert.True(msPerTick < 5.0, $"{msPerTick:0.000} ms por tick");
        Assert.True(stored > 0);
    }
}
