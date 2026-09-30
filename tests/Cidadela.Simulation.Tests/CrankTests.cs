using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Manivela e linhas de esteira movidas a torque (docs/cadeia_flecha.md).</summary>
public class CrankTests
{
    private const string River = """{ "default": "grass", "patches": [{ "kind": "water", "x": 19, "z": 0, "width": 1, "height": 20 }] }""";

    /// <summary>Linha de <paramref name="length"/> esteiras para leste em z = 5 a partir de x = 2; item posto na primeira.</summary>
    private static SimWorld Line(int length, string extra = "", string villagers = "[]")
    {
        var belts = new System.Text.StringBuilder();
        for (int x = 2; x < 2 + length; x++)
            belts.Append($$"""{ "kind": "belt", "x": {{x}}, "z": 5, "direction": "east" },""");
        SimWorld world = TestWorlds.Open(x: 3, z: 3, data: TestWorlds.RealData(), terrain: River,
            buildings: $"[{belts}{extra}]".Replace(",]", "]"), villagers: villagers);
        TestWorlds.Run(world, 2);
        world.Castellan.Inventory.Add("shaft", 1);
        world.Enqueue(new InsertItemCommand(new GridPos(2, 5), "shaft"));
        world.Tick();
        return world;
    }

    private static float Front(SimWorld world) => world.BuildingAt(new GridPos(2, 5))!.Belt!.Items[0].Progress;

    [Fact]
    public void BeltWithoutCrankDoesNotMove()
    {
        SimWorld world = Line(3);
        float before = Front(world);
        TestWorlds.Run(world, 20);
        Assert.Equal(before, Front(world));
        Assert.False(world.BuildingAt(new GridPos(2, 5))!.Line!.Moving);
    }

    [Fact]
    public void MannedCrankMovesTheLine()
    {
        SimWorld world = Line(3, """{ "kind": "crank", "x": 2, "z": 6, "direction": "north" }""", """[{ "x": 2, "z": 7 }]""");
        float before = Front(world);
        TestWorlds.Run(world, 5);
        Assert.True(Front(world) > before);
        Assert.Equal(12, world.BuildingAt(new GridPos(2, 5))!.Line!.Capacity);
    }

    [Fact]
    public void CrankWithoutAnybodyDoesNotMoveTheLine()
    {
        SimWorld world = Line(3, """{ "kind": "crank", "x": 2, "z": 6, "direction": "north" }""");
        float before = Front(world);
        TestWorlds.Run(world, 20);
        Assert.Equal(before, Front(world));
    }

    [Fact]
    public void OneCrankMovesTwelveCellsNotThirteen()
    {
        SimWorld twelve = Line(12, """{ "kind": "crank", "x": 2, "z": 6, "direction": "north" }""", """[{ "x": 2, "z": 7 }]""");
        SimWorld thirteen = Line(13, """{ "kind": "crank", "x": 2, "z": 6, "direction": "north" }""", """[{ "x": 2, "z": 7 }]""");
        Assert.True(twelve.BuildingAt(new GridPos(2, 5))!.Line!.Moving);
        Assert.False(thirteen.BuildingAt(new GridPos(2, 5))!.Line!.Moving);

        SimWorld twoCranks = Line(13, """
            { "kind": "crank", "x": 2, "z": 6, "direction": "north" }, { "kind": "crank", "x": 10, "z": 4, "direction": "south" }
            """, """[{ "x": 2, "z": 7 }, { "x": 10, "z": 3 }]""");
        TestWorlds.Run(twoCranks, 10);
        Assert.True(twoCranks.BuildingAt(new GridPos(2, 5))!.Line!.Moving);
        Assert.Equal(24, twoCranks.BuildingAt(new GridPos(2, 5))!.Line!.Capacity);
    }

    [Fact]
    public void AxleTurnsTheCrankWithoutAVillager()
    {
        // Roda na água (19, 6), eixos até a manivela (4, 6), que aponta para a esteira (4, 5).
        var axles = new System.Text.StringBuilder();
        for (int x = 5; x < 19; x++)
            axles.Append($$""", { "kind": "axle", "x": {{x}}, "z": 6 }""");
        SimWorld world = Line(3, $$"""
            { "kind": "crank", "x": 4, "z": 6, "direction": "north" }, { "kind": "water_wheel", "x": 19, "z": 6 }{{axles}}
            """);
        float before = Front(world);
        TestWorlds.Run(world, 5);
        Assert.True(world.BuildingAt(new GridPos(4, 6))!.Turning);
        Assert.True(Front(world) > before);
    }

    [Fact]
    public void CrankTurnedByTheAxleCallsNobodyAndFreesItsVillager()
    {
        SimWorld world = Line(3, """{ "kind": "crank", "x": 4, "z": 6, "direction": "north" }""", """[{ "x": 4, "z": 7 }]""");
        Villager v = world.Villagers[0];
        Assert.Same(world.BuildingAt(new GridPos(4, 6)), v.Home); // sem eixo, ele gira a manivela

        // Roda e eixos até (6, 6); falta só o eixo (5, 6) para ligar a manivela.
        world.Castellan.Inventory.Add("wood", 40);
        world.Castellan.Inventory.Add("stone", 5);
        // O Castelão (alcance 10) faz a ponta de cá, anda para leste e faz a roda e o resto.
        foreach (int x in new[] { 6, 7, 8, 9, 10, 11, 12 })
            world.Enqueue(new BuildCommand("axle", new GridPos(x, 6), Direction.East));
        world.Tick();
        Assert.Same(world.BuildingAt(new GridPos(4, 6)), v.Home);
        TestWorlds.Move(world, 1f, 0f, 120);
        TestWorlds.Move(world, 0f, 0f, 1);
        world.Enqueue(new BuildCommand("water_wheel", new GridPos(19, 6), Direction.North));
        foreach (int x in new[] { 13, 14, 15, 16, 17, 18 })
            world.Enqueue(new BuildCommand("axle", new GridPos(x, 6), Direction.East));
        world.Tick();
        Assert.Same(world.BuildingAt(new GridPos(4, 6)), v.Home); // ainda falta o eixo (5, 6)
        TestWorlds.Move(world, -1f, 0f, 60);
        TestWorlds.Move(world, 0f, 0f, 1);
        world.Enqueue(new BuildCommand("axle", new GridPos(5, 6), Direction.East));
        TestWorlds.Run(world, 2);
        Assert.True(world.BuildingAt(new GridPos(4, 6))?.Turning ?? false, "a manivela deveria estar na rede");
        Assert.Null(v.Home);
        Assert.True(world.BuildingAt(new GridPos(2, 5))!.Line!.Moving);
    }

    [Fact]
    public void ShowcaseMapRunsBeltsWithoutCranks()
    {
        SimWorld world = MapLoader.Parse("""
            { "width": 8, "height": 8, "castellan": { "x": 1, "z": 1 }, "freeMachines": true,
              "buildings": [{ "kind": "belt", "x": 2, "z": 5, "direction": "east" }, { "kind": "sawmill", "x": 3, "z": 5 }] }
            """, TestWorlds.RealData());
        world.Enqueue(new SpawnItemCommand(new GridPos(2, 5), "wood"));
        TestWorlds.Run(world, 40);
        Assert.True(world.BuildingAt(new GridPos(3, 5))!.Machine!.IsWorking); // tora chegou e a serraria anda sem serradores
    }
}
