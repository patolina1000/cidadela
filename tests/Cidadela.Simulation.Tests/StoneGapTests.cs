using System.Collections.Generic;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Pedra (e veio) bloqueia só a base, um círculo no centro da célula, como o tronco da árvore. Dados de teste: pedra de
/// raio 0,3, tronco 0,15, Castelão de raio 0,3 (0,6 m de largura), aldeão de raio 0,15.
/// Vãos: pedra–pedra lado a lado 0,4 m, na diagonal 0,81; pedra–árvore lado a lado 0,55, na diagonal 0,96.
/// </summary>
public class StoneGapTests
{
    internal static GameData StoneData() => GameData.Parse(TestWorlds.Items,
        TestWorlds.Resources.Replace("\"amount\": 30 }", "\"amount\": 30, \"trunkRadius\": 0.15 }")
            .Replace("\"amount\": 2 }", "\"amount\": 30, \"trunkRadius\": 0.3 }"),
        TestWorlds.CastellanStats.Replace("\"radius\": 0.3", "\"radius\": 0.3, \"gatherSurfaceReach\": 1.3"),
        TestWorlds.VillagerStats, TestWorlds.Buildings, TestWorlds.Recipes);

    private static SimWorld Open(float x, float z, string resources, string buildings = "[]", string villagers = "[]")
    {
        SimWorld world = MapLoader.Parse($$"""
            { "width": 20, "height": 20, "castellan": { "x": 1, "z": 1 }, "resources": {{resources}},
              "buildings": {{buildings}}, "villagers": {{villagers}} }
            """, StoneData());
        world.Castellan.PlaceAt(new Vector2(x, z));
        return world;
    }

    [Fact]
    public void CastellanStopsTouchingTheStoneNotAtTheCellEdge()
    {
        SimWorld world = Open(4f, 6.5f, """[{ "kind": "stone", "x": 4, "z": 4 }]""");
        TestWorlds.Move(world, 0f, -1f, ticks: 12);
        // Corpo 0,3 + pedra 0,3: para a 0,6 do centro (z = 4,6); pela célula inteira pararia em z = 5,3.
        Vector2 p = world.Castellan.Position;
        Assert.InRange(Vector2.Distance(p, new Vector2(4f, 4f)), 0.59f, 0.7f);
    }

    [Theory]
    [InlineData("stone", "stone")]
    [InlineData("stone", "wood")]
    public void CastellanPassesBetweenDiagonalNeighbours(string a, string b)
    {
        SimWorld world = Open(2.5f, 5.7f, $$"""[{ "kind": "{{a}}", "x": 4, "z": 4 }, { "kind": "{{b}}", "x": 5, "z": 5 }]""");
        TestWorlds.Move(world, 1f, -0.6f, ticks: 25);
        Vector2 p = world.Castellan.Position;
        Assert.True(p.X > 6f && p.Y < 3.5f, $"parou em {p}");
    }

    [Theory]
    [InlineData("stone", "stone")] // vão 0,4 < 0,6
    [InlineData("stone", "wood")]  // vão 0,55 < 0,6
    public void CastellanDoesNotSqueezeThroughAGapNarrowerThanHerBody(string a, string b)
    {
        SimWorld world = Open(4.5f, 6.5f, $$"""[{ "kind": "{{a}}", "x": 4, "z": 4 }, { "kind": "{{b}}", "x": 5, "z": 4 }]""");
        TestWorlds.Move(world, 0f, -1f, ticks: 30);
        Assert.True(world.Castellan.Position.Y > 4f, $"atravessou: {world.Castellan.Position}");
    }

    [Fact]
    public void CastellanGathersAStoneFromTheDiagonal()
    {
        SimWorld world = Open(4f, 4f, """[{ "kind": "stone", "x": 5, "z": 5 }]""");
        ResourceNode stone = world.ResourceAt(new GridPos(5, 5))!;
        Assert.True(world.Castellan.CanGather(stone.Cell, stone.BlockRadius));
        world.Enqueue(new GatherCommand(stone.Cell));
        TestWorlds.Run(world, 40);
        Assert.True(world.Castellan.Inventory.Count("stone") >= 1);
    }

    [Theory]
    [InlineData("stone", "stone")] // vão 0,4 > 0,3 do aldeão
    [InlineData("stone", "wood")]  // vão 0,55
    public void VillagerCrossesBetweenNeighbours(string a, string b)
    {
        // O muro é de serrarias (construção sólida: célula inteira); a cabana fica ao norte, a madeira a coletar ao sul, e
        // só um vizinho do vão é madeira quando b = wood; senão, a árvore a coletar fica ao sul do muro.
        var walls = new List<string> { """{ "kind": "lumber_hut", "x": 4, "z": 1 }""" };
        for (int x = 0; x < 20; x++)
            if (x != 4 && x != 5)
                walls.Add($$"""{ "kind": "sawmill", "x": {{x}}, "z": 4 }""");
        string resources = $$"""[{ "kind": "{{a}}", "x": 4, "z": 4 }, { "kind": "{{b}}", "x": 5, "z": 4 }, { "kind": "wood", "x": 4, "z": 7 }]""";
        SimWorld world = Open(18f, 18f, resources, "[" + string.Join(",", walls) + "]", """[{ "x": 8, "z": 2 }]""");
        TestWorlds.Run(world, 900);
        Assert.True(world.BuildingAt(new GridPos(4, 1))!.Workplace!.Stored.Count("wood") >= 2,
            $"estado {world.Villagers[0].Status}, em {world.Villagers[0].Position}");
    }

    [Fact]
    public void VillagerGathersTouchingTheStoneBase()
    {
        // Cabana de lenhador não coleta pedra: aqui só confere o círculo de bloqueio da pedra para o caminho do aldeão.
        SimWorld world = Open(18f, 18f, """[{ "kind": "stone", "x": 4, "z": 4 }]""");
        Assert.False(world.BlocksVillager(new GridPos(4, 4)));
        Assert.Equal(0.3f, world.BlockRadiusAt(new GridPos(4, 4))!.Value, 3);
    }
}
