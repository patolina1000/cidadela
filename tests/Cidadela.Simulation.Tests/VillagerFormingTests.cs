using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>O Cristal-mãe forma aldeões (docs/linha_aldeoes.md): casca + puro + mana; o aldeão nasce livre e vai ao posto.</summary>
public class VillagerFormingTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    /// <summary>Torre em (10, 6) com Relicário em (9, 7) com 12 puros (240 s de mana) e o Cristal-mãe em (11, 5) (dados do jogo).</summary>
    private static SimWorld Crystal(bool powered = true) => MapLoader.Parse($$"""
        { "width": 20, "height": 20, "castellan": { "x": 17, "z": 17 },
          "buildings": [{{(powered ? """{ "kind": "mana_tower", "x": 10, "z": 6 }, { "kind": "reliquary", "x": 9, "z": 7, "items": { "pure_shard": 12 } },""" : "")}}
                        { "kind": "mother_crystal", "x": 11, "z": 5 }] }
        """, TestWorlds.RealData());

    private static Building MotherCrystal(SimWorld world) => world.BuildingAt(new GridPos(11, 5))!;

    [Fact]
    public void AShellAPureShardAndManaFormAFreeVillagerBesideTheCrystal()
    {
        SimWorld world = Crystal();
        Building crystal = MotherCrystal(world);
        crystal.Machine!.Input.Add("shell", 1);
        crystal.Machine.Input.Add("pure_shard", 1);
        TestWorlds.Run(world, Seconds(149f));
        Assert.Empty(world.Villagers);
        Assert.Equal(4f, crystal.ManaDemand); // o sopro: 4/s enquanto forma
        TestWorlds.Run(world, Seconds(2f));
        Villager born = Assert.Single(world.Villagers);
        Assert.Null(born.Home); // livre (não há posto vago)
        Assert.True(System.Math.Abs(born.Cell.X - 11) <= 1 && System.Math.Abs(born.Cell.Z - 5) <= 1);
        Assert.Equal(1, crystal.VillagersFormed);
        Assert.Equal(0f, crystal.ManaDemand); // parado, não gasta
    }

    [Theory]
    [InlineData("shell")]
    [InlineData("pure_shard")]
    public void WithoutTheShellOrThePureShardNothingIsFormed(string only)
    {
        SimWorld world = Crystal();
        MotherCrystal(world).Machine!.Input.Add(only, 2);
        TestWorlds.Run(world, Seconds(160f));
        Assert.Empty(world.Villagers);
        Assert.Equal(MachineWait.MissingInput, MotherCrystal(world).Machine!.Waiting);
    }

    [Fact]
    public void WithoutManaNothingIsFormed()
    {
        SimWorld world = Crystal(powered: false);
        MotherCrystal(world).Machine!.Input.Add("shell", 1);
        MotherCrystal(world).Machine!.Input.Add("pure_shard", 1);
        TestWorlds.Run(world, Seconds(160f));
        Assert.Empty(world.Villagers);
        Assert.Equal(MachineWait.NoMana, MotherCrystal(world).Machine!.Waiting);
    }

    [Fact]
    public void ItHoldsUpToTwoShellsAndTwoPureShards()
    {
        MachineState crystal = MotherCrystal(Crystal()).Machine!;
        Assert.Equal(2, crystal.Room("shell"));
        Assert.Equal(2, crystal.Room("pure_shard"));
        Assert.Equal(0, crystal.Room("water_jar"));
    }

    [Fact]
    public void AWeakNetworkFormsMoreSlowly()
    {
        // Dados de teste: gerador 10/s e um berço que pede 20/s: metade da mana, o dobro do tempo (20 s em vez de 10).
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: """
            [{ "kind": "tower", "x": 10, "z": 10 }, { "kind": "generator", "x": 9, "z": 9 }, { "kind": "cradle", "x": 11, "z": 11 }]
            """);
        MachineState cradle = world.BuildingAt(new GridPos(11, 11))!.Machine!;
        cradle.Input.Add("wood", 1);
        cradle.Input.Add("shaft", 1);
        TestWorlds.Run(world, Seconds(15f));
        Assert.Empty(world.Villagers);
        TestWorlds.Run(world, Seconds(5.5f));
        Assert.Single(world.Villagers);
    }

    [Fact]
    public void TheNewVillagerTakesAnEmptyPost()
    {
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: """
            [{ "kind": "tower", "x": 10, "z": 10 }, { "kind": "generator", "x": 9, "z": 9 }, { "kind": "cradle", "x": 11, "z": 11 },
             { "kind": "press", "x": 15, "z": 11 }]
            """);
        MachineState cradle = world.BuildingAt(new GridPos(11, 11))!.Machine!;
        cradle.Input.Add("wood", 1);
        cradle.Input.Add("shaft", 1);
        TestWorlds.Run(world, Seconds(25f));
        Villager born = Assert.Single(world.Villagers);
        Assert.Same(world.BuildingAt(new GridPos(15, 11)), born.Home);
        TestWorlds.Run(world, Seconds(5f));
        Assert.Equal(VillagerTask.AtPost, born.Task);
    }

    [Fact]
    public void WithoutAFreeCellBesideItTheVillagerWaitsInside()
    {
        // Berço cercado de baús nas 8 vizinhas: o aldeão pronto espera; tirar um baú abre espaço e ele nasce.
        string chests = string.Join(", ", new[] { (10, 10), (11, 10), (12, 10), (10, 11), (12, 11), (10, 12), (11, 12), (12, 12) }
            .Select(c => $$"""{ "kind": "chest", "x": {{c.Item1}}, "z": {{c.Item2}} }"""));
        SimWorld world = TestWorlds.Open(x: 14, z: 14, buildings: $$"""
            [{ "kind": "tower", "x": 13, "z": 9 }, { "kind": "generator", "x": 14, "z": 9 }, { "kind": "cradle", "x": 11, "z": 11 }, {{chests}}]
            """);
        Building cradle = world.BuildingAt(new GridPos(11, 11))!;
        cradle.Machine!.Input.Add("wood", 2);
        cradle.Machine.Input.Add("shaft", 2);
        TestWorlds.Run(world, Seconds(25f));
        Assert.Empty(world.Villagers);
        Assert.Equal(1, cradle.PendingVillagers);
        Assert.Equal(MachineWait.NoRoom, cradle.Machine.Waiting);
        Assert.Equal(1, cradle.Machine.Input.Count("wood")); // não começa o próximo enquanto um espera

        world.Enqueue(new DeconstructCommand(new GridPos(12, 12)));
        TestWorlds.Run(world, 2);
        Villager born = Assert.Single(world.Villagers);
        Assert.Equal(new GridPos(12, 12), born.Cell);
    }
}
