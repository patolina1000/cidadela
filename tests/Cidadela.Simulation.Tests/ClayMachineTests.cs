using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Barreiro e Oleiro (docs/linha_aldeoes.md) com os números do jogo.</summary>
public class ClayMachineTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    /// <summary>
    /// Mapa 20×20: água em x = 0, margem em x = 1 (z 2–12); torre em (3, 6) (área x 1–5, z 4–8) e Relicário cheio em
    /// (4, 7); as construções e aldeões dados.
    /// </summary>
    private static SimWorld World(string buildings, string villagers = "[]")
    {
        SimWorld world = MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 10, "z": 10 },
          "buildings": [{ "kind": "mana_tower", "x": 3, "z": 6 }, { "kind": "reliquary", "x": 4, "z": 7, "items": { "pure_shard": 5 } }{{buildings}}],
          "villagers": {{villagers}},
          "terrain": { "default": "grass", "patches": [{ "kind": "water", "x": 0, "z": 0, "width": 1, "height": 20 },
                                                      { "kind": "bank", "x": 1, "z": 2, "width": 1, "height": 11 }] } }
        """, TestWorlds.RealData());
        TestWorlds.OperateNearest(world); // os aldeões do teste são os operadores das máquinas encostadas neles
        return world;
    }

    [Fact]
    public void TheClayPitIsBuiltOnlyOnTheBank()
    {
        SimWorld world = World("");
        world.Castellan.PlaceAt(new System.Numerics.Vector2(3f, 10f));
        world.Castellan.Inventory.Add("stone", 10);
        BuildingType pit = world.Data.Building("clay_pit");
        Assert.Equal(BuildCheck.Ok, world.CanBuild(pit, new GridPos(1, 10)));
        Assert.Equal(BuildCheck.WrongGround, world.CanBuild(pit, new GridPos(2, 10)));
        Assert.Equal(BuildCheck.WrongGround, world.CanBuild(pit, new GridPos(1, 15))); // encostado na água, mas não é margem
    }

    [Fact]
    public void TheClayPitDigsOneClayEverySixSecondsAndKeepsIt()
    {
        SimWorld world = World(""", { "kind": "clay_pit", "x": 1, "z": 5 }""", """[{ "x": 2, "z": 5 }]""");
        MachineState pit = world.BuildingAt(new GridPos(1, 5))!.Machine!;
        TestWorlds.Run(world, Seconds(18f) + 5);
        Assert.Equal(3, pit.Output.Count("clay"));
        TestWorlds.Run(world, Seconds(60f));
        Assert.Equal(5, pit.Output.Count("clay")); // guarda até 5 e para: ninguém tira
        Assert.False(pit.IsWorking);
        Assert.False(pit.CanStart); // saída cheia (o operador solta o posto e a ladainha dele segue)
    }

    [Fact]
    public void ThePotterNeedsManaAndAnOperator()
    {
        // Sem operador:
        SimWorld alone = World(""", { "kind": "potter", "x": 3, "z": 5 }""");
        MachineState idle = alone.BuildingAt(new GridPos(3, 5))!.Machine!;
        idle.Input.Add("clay", 2);
        idle.Input.Add("water_jar", 1);
        TestWorlds.Run(alone, Seconds(20f));
        Assert.Equal(MachineWait.PostsEmpty, idle.Waiting);

        // Com operador e mana: 1 casca em 15 s.
        SimWorld world = World(""", { "kind": "potter", "x": 3, "z": 5 }""", """[{ "x": 3, "z": 4 }]""");
        MachineState potter = world.BuildingAt(new GridPos(3, 5))!.Machine!;
        potter.Input.Add("clay", 4);
        potter.Input.Add("water_jar", 2);
        TestWorlds.Run(world, Seconds(15f) + 5);
        Assert.Equal(1, potter.Output.Count("shell"));
        Assert.Equal(2, world.BuildingAt(new GridPos(3, 5))!.Type.Mana!.Use);
    }

    [Fact]
    public void ThePotterWithoutManaDoesNotWork()
    {
        SimWorld world = MapLoader.Parse("""
            { "width": 20, "height": 20, "castellan": { "x": 10, "z": 10 },
              "buildings": [{ "kind": "potter", "x": 3, "z": 5 }], "villagers": [{ "x": 3, "z": 4 }] }
            """, TestWorlds.RealData());
        TestWorlds.OperateNearest(world);
        MachineState potter = world.BuildingAt(new GridPos(3, 5))!.Machine!;
        potter.Input.Add("clay", 2);
        potter.Input.Add("water_jar", 1);
        TestWorlds.Run(world, Seconds(20f));
        Assert.Equal(MachineWait.NoMana, potter.Waiting);
        Assert.Equal(0, potter.Output.Count("shell"));
    }
}
