using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>Bruto x processado: tora, pedra e minério não entram em esteira.</summary>
public class RawItemTests
{
    [Fact]
    public void RawItemsAreMarkedInTheData()
    {
        GameData data = TestWorlds.RealData();
        Assert.True(data.Item("wood").Raw);
        Assert.True(data.Item("stone").Raw);
        Assert.True(data.Item("iron").Raw);
        Assert.False(data.Item("shaft").Raw);
        Assert.False(data.Item("ingot").Raw);
    }

    [Fact]
    public void CastellanCannotPutRawOnABelt()
    {
        SimWorld world = TestWorlds.Open(x: 4, z: 4, data: TestWorlds.RealData(),
            buildings: """[{ "kind": "belt", "x": 6, "z": 4, "direction": "east" }]""");
        world.Castellan.Inventory.Add("wood", 3);
        world.Castellan.Inventory.Add("shaft", 3);
        world.Enqueue(new InsertItemCommand(new GridPos(6, 4), "wood"));
        world.Tick();
        Assert.Empty(world.BuildingAt(new GridPos(6, 4))!.Belt!.Items);
        Assert.Equal(3, world.Castellan.Inventory.Count("wood"));

        world.Enqueue(new InsertItemCommand(new GridPos(6, 4), "shaft"));
        world.Tick();
        Assert.Single(world.BuildingAt(new GridPos(6, 4))!.Belt!.Items);
    }

    [Fact]
    public void HutDoesNotPushRawOntoABeltButFillsAChest()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, data: TestWorlds.RealData(), buildings: """
            [{ "kind": "lumber_hut", "x": 5, "z": 5, "direction": "east" },
             { "kind": "belt", "x": 6, "z": 5, "direction": "east" },
             { "kind": "lumber_hut", "x": 5, "z": 9, "direction": "east" },
             { "kind": "chest", "x": 6, "z": 9 }]
            """);
        Building beltHut = world.BuildingAt(new GridPos(5, 5))!, chestHut = world.BuildingAt(new GridPos(5, 9))!;
        beltHut.Workplace!.Stored.Add("wood", 4);
        chestHut.Workplace!.Stored.Add("wood", 4);
        TestWorlds.Run(world, 10);
        Assert.Empty(world.BuildingAt(new GridPos(6, 5))!.Belt!.Items);
        Assert.Equal(4, beltHut.Workplace.Stored.Count("wood"));
        Assert.Equal(4, world.BuildingAt(new GridPos(6, 9))!.Storage!.Count("wood"));
    }
}
