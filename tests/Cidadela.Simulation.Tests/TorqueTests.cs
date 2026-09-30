using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Água, roda d'água, eixo e redes de torque (docs/cadeia_flecha.md).</summary>
public class TorqueTests
{
    /// <summary>Rio na coluna x = 10 (água de z 0 a 19); o Castelão em (8, 5), perto dele.</summary>
    private const string River = """{ "default": "grass", "patches": [{ "kind": "water", "x": 10, "z": 0, "width": 1, "height": 20 }] }""";

    private static SimWorld World(string buildings = "[]", string villagers = "[]")
    {
        SimWorld world = TestWorlds.Open(x: 8, z: 5, data: TestWorlds.RealData(), terrain: River, buildings: buildings,
            villagers: villagers);
        world.Castellan.Inventory.Add("wood", 100);
        world.Castellan.Inventory.Add("stone", 100);
        return world;
    }

    [Fact]
    public void WaterWheelOnlyOnWaterAndNothingElseOnWater()
    {
        SimWorld world = World();
        GameData data = world.Data;
        Assert.Equal(BuildCheck.Ok, world.CanBuild(data.Building("water_wheel"), new GridPos(10, 5)));
        Assert.Equal(BuildCheck.WrongGround, world.CanBuild(data.Building("water_wheel"), new GridPos(9, 5)));
        Assert.Equal(BuildCheck.WrongGround, world.CanBuild(data.Building("axle"), new GridPos(10, 6)));
        Assert.Equal(BuildCheck.Ok, world.CanBuild(data.Building("axle"), new GridPos(9, 5)));
    }

    [Fact]
    public void NobodyWalksOnWater()
    {
        SimWorld world = World();
        Assert.True(world.IsSolid(new GridPos(10, 3)));
        Assert.True(world.BlocksVillager(new GridPos(10, 3)));
        TestWorlds.Move(world, 1f, 0f, 60);
        Assert.True(world.Castellan.Position.X < 9.6f);
    }

    [Fact]
    public void WheelAxlesAndSmelterMakeOneTurningNetwork()
    {
        SimWorld world = World("""
            [{ "kind": "water_wheel", "x": 10, "z": 8 }, { "kind": "axle", "x": 9, "z": 8 }, { "kind": "axle", "x": 8, "z": 8 },
             { "kind": "smelter", "x": 7, "z": 8 }, { "kind": "axle", "x": 5, "z": 12 }]
            """);
        world.Tick();
        Building smelter = world.BuildingAt(new GridPos(7, 8))!;
        Assert.True(smelter.Turning);
        Assert.Same(world.BuildingAt(new GridPos(10, 8))!.Network, smelter.Network);
        Assert.Equal(16f, smelter.Network!.Supply);
        Assert.Equal(4f, smelter.Network.Demand);
        Assert.False(world.BuildingAt(new GridPos(5, 12))!.Turning); // eixo solto, sem roda
    }

    [Fact]
    public void OverloadedNetworkStopsWhole()
    {
        // 16 de força contra 5 fundições × 4 = 20 de demanda.
        SimWorld world = World("""
            [{ "kind": "water_wheel", "x": 10, "z": 8 }, { "kind": "axle", "x": 9, "z": 8 },
             { "kind": "smelter", "x": 8, "z": 8 }, { "kind": "smelter", "x": 8, "z": 7 }, { "kind": "smelter", "x": 8, "z": 9 },
             { "kind": "smelter", "x": 7, "z": 8 }, { "kind": "smelter", "x": 6, "z": 8 }]
            """);
        world.Tick();
        Assert.False(world.BuildingAt(new GridPos(9, 8))!.Turning);
        Assert.Equal(20f, world.BuildingAt(new GridPos(9, 8))!.Network!.Demand);
    }

    [Fact]
    public void NetworkIsRebuiltWhenABuildingGoesAway()
    {
        SimWorld world = World("""
            [{ "kind": "water_wheel", "x": 10, "z": 5 }, { "kind": "axle", "x": 9, "z": 5 }, { "kind": "smelter", "x": 8, "z": 6 }]
            """);
        world.Tick();
        Building smelter = world.BuildingAt(new GridPos(8, 6))!;
        Assert.False(smelter.Turning); // (8, 6) não encosta no eixo (9, 5)
        world.Enqueue(new BuildCommand("axle", new GridPos(9, 6), Direction.North));
        world.Tick();
        world.Tick();
        Assert.True(smelter.Turning);
        world.Enqueue(new DeconstructCommand(new GridPos(9, 6)));
        world.Tick();
        world.Tick();
        Assert.False(smelter.Turning);
    }

    [Fact]
    public void BellowsMakeTheSmelterHalfFaster()
    {
        SimWorld world = World("""
            [{ "kind": "water_wheel", "x": 10, "z": 8 }, { "kind": "axle", "x": 9, "z": 8 }, { "kind": "smelter", "x": 8, "z": 8 },
             { "kind": "smelter", "x": 6, "z": 3 }]
            """, villagers: """[{ "x": 8, "z": 9 }, { "x": 6, "z": 4 }]""");
        TestWorlds.Run(world, 2);
        MachineState withBellows = world.BuildingAt(new GridPos(8, 8))!.Machine!, without = world.BuildingAt(new GridPos(6, 3))!.Machine!;
        foreach (MachineState m in new[] { withBellows, without })
        {
            m.Input.Add("iron", 1);
            m.Input.Add("charcoal", 1);
        }
        TestWorlds.Run(world, 10 * SimClock.TicksPerSecond + 1); // 15 s ÷ 1,5 = 10 s
        Assert.Equal(1, withBellows.Output.Count("ingot"));
        Assert.Equal(0, without.Output.Count("ingot"));
        Assert.Equal(1.5f, withBellows.Speed);
    }
}
