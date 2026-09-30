using Xunit;

namespace Cidadela.Simulation.Tests;

public class MachineTests
{
    // Serraria de teste em (6, 4): 1 madeira → 2 hastes em 20 ticks. Castelão em (4, 4).
    private static readonly GridPos Mill = new(6, 4);

    private static SimWorld World(string extra = "", string millDirection = "east", int wood = 10)
    {
        string buildings = $$"""[{ "kind": "sawmill", "x": 6, "z": 4, "direction": "{{millDirection}}" }{{extra}}]""";
        SimWorld world = TestWorlds.Open(x: 4, z: 4, buildings: buildings);
        world.Castellan.Inventory.Add("wood", wood);
        return world;
    }

    private static MachineState Machine(SimWorld world) => world.BuildingAt(Mill)!.Machine!;

    private static void Insert(SimWorld world, GridPos cell)
    {
        world.Enqueue(new InsertItemCommand(cell, "wood"));
        world.Tick();
    }

    [Fact]
    public void CraftsAfterTheRecipeTime()
    {
        SimWorld world = World();
        Insert(world, Mill); // entra, começa e já conta 1 tick
        Assert.True(Machine(world).IsWorking);
        TestWorlds.Run(world, 18);
        Assert.Equal(0, Machine(world).Output.Count("shaft"));
        world.Tick();
        Assert.Equal(2, Machine(world).Output.Count("shaft"));
        Assert.False(Machine(world).IsWorking);
    }

    [Fact]
    public void WaitsForInputs()
    {
        SimWorld world = World();
        TestWorlds.Run(world, 40);
        Assert.False(Machine(world).IsWorking);
        Assert.Equal(MachineWait.MissingInput, Machine(world).Waiting);
    }

    [Fact]
    public void AcceptsOnlyItsInputsUpToTwoCycles()
    {
        SimWorld world = World();
        MachineState machine = Machine(world);
        Assert.False(machine.Accepts("stone"));
        machine.Input.Add("wood", 2);
        Assert.False(machine.Accepts("wood"));
    }

    [Fact]
    public void StopsWhenTheOutputIsFull()
    {
        SimWorld world = World(wood: 20);
        MachineState machine = Machine(world);
        for (int i = 0; i < 8; i++)
        {
            Insert(world, Mill);
            TestWorlds.Run(world, 20);
        }
        Assert.Equal(2 * MachineState.OutputCycles, machine.Output.Count("shaft"));
        Assert.Equal(MachineWait.OutputFull, machine.Waiting);
    }

    [Fact]
    public void NeverPushesOutputIntoAChest()
    {
        // As máquinas guardam o que produzem: tudo sai pela mão (docs/ladainhas.md).
        SimWorld chest = World(extra: """, { "kind": "chest", "x": 7, "z": 4 }""");
        Insert(chest, Mill);
        TestWorlds.Run(chest, 40);
        Assert.True(chest.BuildingAt(new GridPos(7, 4))!.Storage!.IsEmpty);
        Assert.Equal(2, Machine(chest).Output.Count("shaft"));
    }

    [Fact]
    public void TheCastellanTakesTheOutput()
    {
        SimWorld world = World();
        Insert(world, Mill);
        TestWorlds.Run(world, 20);
        world.Enqueue(new TakeAllCommand(Mill));
        world.Tick();
        Assert.Equal(2, world.Castellan.Inventory.Count("shaft"));
    }

    [Fact]
    public void TakingTheOutputLeavesInputsAndTheCycleInTheMachine()
    {
        SimWorld world = World(wood: 3);
        Insert(world, Mill);
        TestWorlds.Run(world, 20);           // 1º ciclo pronto: 2 hastes
        Insert(world, Mill);                 // 2º ciclo começa
        Insert(world, Mill);                 // 1 madeira esperando
        world.Enqueue(new TakeAllCommand(Mill));
        world.Tick();

        Assert.Equal(2, world.Castellan.Inventory.Count("shaft"));
        Assert.Equal(0, world.Castellan.Inventory.Count("wood"));
        Assert.True(Machine(world).IsWorking);
        Assert.Equal(1, Machine(world).Input.Count("wood"));
    }

    [Fact]
    public void DeconstructingReturnsInputsOutputsAndTheCycleInProgress()
    {
        SimWorld world = World(wood: 3);
        Insert(world, Mill);               // começa um ciclo (1 madeira em trabalho)
        Insert(world, Mill);               // 1 madeira esperando na entrada
        world.Enqueue(new DeconstructCommand(Mill));
        world.Tick();
        // 3 madeiras de volta (1 que sobrou + 1 em trabalho + 1 na entrada) + custo (8).
        Assert.Equal(11, world.Castellan.Inventory.Count("wood"));
    }
}
