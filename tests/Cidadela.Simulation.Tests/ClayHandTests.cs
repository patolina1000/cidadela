using System.Linq;
using System.Numerics;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Ações à mão da linha 2 (docs/linha_aldeoes.md): cavar argila, moldar a casca perto da água, formar o 1º aldeão.</summary>
public class ClayHandTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    /// <summary>20×20: água em x 0–1, margem em x = 2 (z 0–19); veio em (8, 4); Cristal-mãe em (10, 10); ela em (3, 10).</summary>
    private static SimWorld World(string buildings = """, { "kind": "mother_crystal", "x": 10, "z": 10 }""") => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 3, "z": 10 },
          "resources": [{ "kind": "rotten_shard", "x": 8, "z": 4 }],
          "buildings": [{{buildings.TrimStart(',', ' ')}}],
          "terrain": { "default": "grass", "patches": [{ "kind": "water", "x": 0, "z": 0, "width": 2, "height": 20 },
                                                      { "kind": "bank", "x": 2, "z": 0, "width": 1, "height": 20 }] } }
        """, TestWorlds.RealData());

    [Fact]
    public void DiggingTheBankGivesOneClayEveryThreeSecondsForever()
    {
        SimWorld world = World();
        world.Enqueue(new GatherCommand(new GridPos(2, 10)));
        TestWorlds.Run(world, Seconds(3f) + 1);
        Assert.Equal(1, world.Castellan.Inventory.Count("clay"));
        TestWorlds.Run(world, Seconds(27f));
        Assert.Equal(10, world.Castellan.Inventory.Count("clay")); // não esgota
    }

    [Fact]
    public void GrassIsNotDug()
    {
        SimWorld world = World();
        world.Enqueue(new GatherCommand(new GridPos(4, 10)));
        TestWorlds.Run(world, Seconds(5f));
        Assert.Equal(0, world.Castellan.Inventory.Count("clay"));
        Assert.Null(world.Castellan.DigCell);
    }

    [Fact]
    public void WalkingStopsTheDigging()
    {
        SimWorld world = World();
        world.Enqueue(new GatherCommand(new GridPos(2, 10)));
        TestWorlds.Run(world, Seconds(1f));
        TestWorlds.Move(world, 1f, 0f, ticks: 2);
        Assert.Null(world.Castellan.DigCell);
    }

    [Fact]
    public void MoldingAShellTakesTwentySecondsNextToWater()
    {
        SimWorld world = World();
        world.Castellan.Inventory.Add("clay", 2);
        world.Enqueue(new HandCraftCommand("mold"));
        TestWorlds.Run(world, Seconds(20f) + 1);
        Assert.Equal(1, world.Castellan.Inventory.Count("shell"));
        Assert.Equal(0, world.Castellan.Inventory.Count("clay"));
        Assert.Equal(0, world.Castellan.Inventory.Count("water_jar")); // sem jarro
    }

    [Fact]
    public void MoldingNeedsWaterWithinTwoCells()
    {
        SimWorld world = World();
        world.Castellan.PlaceAt(new Vector2(4f, 10f)); // a água mais perto (x = 1) fica a 3 células
        world.Castellan.Inventory.Add("clay", 2);
        world.Enqueue(new HandCraftCommand("mold"));
        TestWorlds.Run(world, Seconds(30f));
        Assert.Equal(0, world.Castellan.Inventory.Count("shell"));
        Assert.True(world.Castellan.HandNeedsWater);
        Assert.Equal(2, world.Castellan.Inventory.Count("clay")); // não começou

        world.Castellan.PlaceAt(new Vector2(3f, 10f)); // a 2 células
        TestWorlds.Run(world, Seconds(20f) + 2);
        Assert.Equal(1, world.Castellan.Inventory.Count("shell"));
    }

    [Fact]
    public void SheCanPutAShellAndAPureShardIntoTheMotherCrystal()
    {
        SimWorld world = World();
        world.Castellan.PlaceAt(new Vector2(9f, 10f));
        world.Castellan.Inventory.Add("shell", 1);
        world.Castellan.Inventory.Add("pure_shard", 1);
        world.Enqueue(new InsertItemCommand(new GridPos(10, 10), "shell"));
        world.Enqueue(new InsertItemCommand(new GridPos(10, 10), "pure_shard"));
        world.Tick();
        MachineState crystal = world.BuildingAt(new GridPos(10, 10))!.Machine!;
        Assert.Equal(1, crystal.Input.Count("shell"));
        Assert.Equal(1, crystal.Input.Count("pure_shard"));
    }

    [Fact]
    public void SheFormsTheFirstVillagerWithHerOwnHands()
    {
        // Sem aldeões e sem máquinas de produção: ela arranca podres, purifica, cava argila, molda a casca, constrói o
        // Relicário e uma torre (as pedras e toras já estão com ela), alimenta o Relicário e forma o aldeão.
        SimWorld world = World();
        Castellan she = world.Castellan;
        she.Inventory.Add("stone", 10);
        she.Inventory.Add("wood", 2);

        // Podres: 30 (15 puros = 5 do Relicário + 1 da torre + 1 do aldeão + 8 de combustível para 150 s).
        she.PlaceAt(new Vector2(7f, 4f));
        world.Enqueue(new GatherCommand(new GridPos(8, 4)));
        for (int i = 0; i < Seconds(200f) && she.Inventory.Count("rotten_shard") < 30; i++)
            world.Tick();
        for (int i = 0; i < 15; i++)
            world.Enqueue(new HandCraftCommand("purify"));
        TestWorlds.Run(world, Seconds(15 * 6f) + 20);
        Assert.Equal(15, she.Inventory.Count("pure_shard"));

        // Argila na margem e a casca moldada ali mesmo.
        she.PlaceAt(new Vector2(3f, 10f));
        world.Enqueue(new GatherCommand(new GridPos(2, 10)));
        TestWorlds.Run(world, Seconds(6f) + 2);
        TestWorlds.Move(world, 0f, 0f, ticks: 1);
        world.Enqueue(new HandCraftCommand("mold"));
        TestWorlds.Run(world, Seconds(20f) + 2);
        Assert.Equal(1, she.Inventory.Count("shell"));

        // Relicário e torre ao lado do Cristal-mãe; combustível, casca e puro.
        she.PlaceAt(new Vector2(8f, 12f));
        world.Enqueue(new BuildCommand("reliquary", new GridPos(8, 10), Direction.North));
        world.Enqueue(new BuildCommand("mana_tower", new GridPos(9, 11), Direction.North));
        world.Tick();
        for (int i = 0; i < 5; i++)
            world.Enqueue(new InsertItemCommand(new GridPos(8, 10), "pure_shard"));
        world.Enqueue(new InsertItemCommand(new GridPos(10, 10), "shell"));
        world.Enqueue(new InsertItemCommand(new GridPos(10, 10), "pure_shard"));
        TestWorlds.Run(world, Seconds(90f));
        for (int i = 0; i < 3; i++)
            world.Enqueue(new InsertItemCommand(new GridPos(8, 10), "pure_shard"));
        TestWorlds.Run(world, Seconds(65f));

        Villager first = Assert.Single(world.Villagers);
        Assert.Equal(1, world.BuildingAt(new GridPos(10, 10))!.VillagersFormed);
        Assert.Null(first.Home);
    }
}
