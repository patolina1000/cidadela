using System.Linq;
using Xunit;

namespace Cidadela.Simulation.Tests;

/// <summary>
/// Máquinas da linha da energia com os números do jogo (docs/linha_energia.md): Relicário, Mina, Poço, Purificador e
/// Cristal-mãe; mana E operador; a conta de mana.
/// </summary>
public class EnergyMachineTests
{
    private static int Seconds(float s) => (int)System.MathF.Round(s * SimClock.TicksPerSecond);

    private static string At(string kind, int x, int z, string extra = "") =>
        $$"""{ "kind": "{{kind}}", "x": {{x}}, "z": {{z}}{{extra}} }""";

    /// <summary>Mapa 20×20 com água na coluna x = 0, veio em (10, 4) e as construções dadas.</summary>
    private static SimWorld World(string buildings, string villagers = "[]")
    {
        SimWorld world = MapLoader.Parse($$"""
            { "width": 20, "height": 20, "castellan": { "x": 17, "z": 17 },
              "resources": [{ "kind": "rotten_shard", "x": 10, "z": 4 }],
              "buildings": [{{buildings}}], "villagers": {{villagers}},
              "terrain": { "default": "grass", "patches": [{ "kind": "water", "x": 0, "z": 0, "width": 1, "height": 20 }] } }
            """, TestWorlds.RealData());
        return world;
    }

    /// <summary>Torre em (10, 6) (área x 8–12, z 4–8) com um Relicário cheio em (9, 7), e as máquinas dadas.</summary>
    private static string Powered(string machines) =>
        $"{At("mana_tower", 10, 6)}, {At("reliquary", 9, 7, ", \"items\": { \"pure_shard\": 5 }")}, {machines}";

    [Fact]
    public void PurifierNeedsSomeoneAtThePost()
    {
        SimWorld world = World(Powered(At("purifier", 11, 7)));
        MachineState purifier = world.BuildingAt(new GridPos(11, 7))!.Machine!;
        purifier.Input.Add("rotten_shard", 2);
        purifier.Input.Add("water_jar", 1);
        TestWorlds.Run(world, Seconds(15f));
        Assert.Equal(0, purifier.Output.Count("pure_shard"));
        Assert.Equal(MachineWait.PostsEmpty, purifier.Waiting);
    }

    [Fact]
    public void PurifierNeedsMana()
    {
        // Operador no posto, mas nenhuma torre.
        SimWorld world = World(At("purifier", 11, 7), """[{ "x": 12, "z": 7 }]""");
        MachineState purifier = world.BuildingAt(new GridPos(11, 7))!.Machine!;
        purifier.Input.Add("rotten_shard", 2);
        purifier.Input.Add("water_jar", 1);
        TestWorlds.Run(world, Seconds(15f));
        Assert.Equal(0, purifier.Output.Count("pure_shard"));
        Assert.Equal(MachineWait.NoMana, purifier.Waiting);
        Assert.Equal(2, purifier.Input.Count("rotten_shard")); // sem mana não gasta as entradas
    }

    [Fact]
    public void PurifierWorksWithManaAndOperator()
    {
        SimWorld world = World(Powered(At("purifier", 11, 7)), """[{ "x": 12, "z": 7 }]""");
        MachineState purifier = world.BuildingAt(new GridPos(11, 7))!.Machine!;
        purifier.Input.Add("rotten_shard", 2);
        purifier.Input.Add("water_jar", 1);
        TestWorlds.Run(world, Seconds(10f) + 5);
        Assert.Equal(1, purifier.Output.Count("pure_shard"));
    }

    [Fact]
    public void HalfTheManaTakesTwiceTheTime()
    {
        // Dados de teste: gerador 10/s e uma serraria que pede 20/s: recebe metade e leva 2 s em vez de 1.
        SimWorld world = TestWorlds.Open(x: 1, z: 1, buildings: """
            [{ "kind": "tower", "x": 10, "z": 10 }, { "kind": "generator", "x": 9, "z": 9 }, { "kind": "powered_mill", "x": 11, "z": 11 }]
            """);
        MachineState mill = world.BuildingAt(new GridPos(11, 11))!.Machine!;
        mill.Input.Add("wood", 1);
        TestWorlds.Run(world, Seconds(1.5f));
        Assert.Equal(0, mill.Output.Count("shaft"));
        Assert.Equal(0.5f, world.BuildingAt(new GridPos(11, 11))!.ManaSatisfaction, 3);
        TestWorlds.Run(world, Seconds(0.5f) + 2);
        Assert.Equal(1, mill.Output.Count("shaft"));
    }

    [Fact]
    public void ReliquaryBurnsAloneThreePerMinuteAndStopsWhenEmpty()
    {
        SimWorld world = World($"{At("mana_tower", 10, 10)}, {At("reliquary", 9, 9, ", \"items\": { \"pure_shard\": 4 }")}");
        Building reliquary = world.BuildingAt(new GridPos(9, 9))!;
        world.Tick();
        world.Tick(); // a geração aparece na soma do tick seguinte ao que o ciclo começa
        Assert.Equal(10f, world.ManaNetworks.Single().Supply);
        TestWorlds.Run(world, Seconds(60f) - 2);
        // 3 ciclos de 20 s em 1 minuto: o 4º começa agora.
        Assert.Equal(1, reliquary.Machine!.Input.Count("pure_shard"));
        TestWorlds.Run(world, Seconds(41f));
        Assert.Equal(0f, world.ManaNetworks.Single().Supply);
        Assert.False(reliquary.Machine.IsWorking);
    }

    [Fact]
    public void TheSurplusIsWhatTheConsumersDoNotUse()
    {
        // Relicário 10/s e a mina trabalhando (2/s): sobram 8/s (e se perdem; o Cristal-mãe não guarda mais mana).
        SimWorld world = World($"{At("mana_tower", 10, 6)}, {At("reliquary", 9, 7, ", \"items\": { \"pure_shard\": 5 }")}, " +
            $"{At("crystal_mine", 10, 4)}", """[{ "x": 11, "z": 4 }]""");
        TestWorlds.Run(world, Seconds(2f));
        Assert.Equal(8f, world.ManaNetworks.Single().Surplus, 3);
    }

    [Fact]
    public void TheMotherCrystalCannotBeDeconstructed()
    {
        SimWorld world = World(At("mother_crystal", 16, 16));
        world.Enqueue(new DeconstructCommand(new GridPos(16, 16)));
        world.Tick();
        Assert.NotNull(world.BuildingAt(new GridPos(16, 16)));
    }

    [Fact]
    public void TheMineIsBuiltOnlyOnTheVeinAndTheWellOnlyBesideWater()
    {
        SimWorld world = World("");
        world.Castellan.PlaceAt(new System.Numerics.Vector2(5f, 5f));
        BuildingType mine = world.Data.Building("crystal_mine"), well = world.Data.Building("well");
        Assert.Equal(BuildCheck.WrongGround, world.CanBuild(mine, new GridPos(6, 6)));
        world.Castellan.Inventory.Add("stone", 20);
        world.Castellan.Inventory.Add("wood", 5);
        Assert.Equal(BuildCheck.Ok, world.CanBuild(mine, new GridPos(10, 4)));
        Assert.Equal(BuildCheck.Ok, world.CanBuild(well, new GridPos(1, 5)));
        Assert.Equal(BuildCheck.WrongGround, world.CanBuild(well, new GridPos(2, 5)));
        Assert.Equal(BuildCheck.WrongGround, world.CanBuild(well, new GridPos(0, 5))); // em cima da água, não
        Assert.Equal(BuildCheck.Occupied, world.CanBuild(world.Data.Building("chest"), new GridPos(10, 4))); // veio ocupa
    }

    [Fact]
    public void TheMineTakesFromTheVeinAndStopsWhenItIsExhausted()
    {
        SimWorld world = World(Powered(At("crystal_mine", 10, 4)), """[{ "x": 11, "z": 4 }]""");
        Building mine = world.BuildingAt(new GridPos(10, 4))!;
        ResourceNode vein = mine.Source!;
        int start = vein.Remaining;
        TestWorlds.Run(world, Seconds(10f) + 5);
        Assert.Equal(2, mine.Machine!.Output.Count("rotten_shard"));
        Assert.Equal(start - 3, vein.Remaining); // 2 prontos + 1 em andamento

        while (vein.TakeOne()) { }
        mine.Machine.Output.MoveAllTo(new Inventory());
        TestWorlds.Run(world, Seconds(6f));
        Assert.Equal(MachineWait.SourceDepleted, mine.Machine.Waiting);
        TestWorlds.Run(world, Seconds(10f));
        Assert.Equal(1, mine.Machine.Output.Count("rotten_shard")); // só o ciclo que já tinha começado
    }

    [Fact]
    public void NobodyGathersFromTheVeinUnderTheMine()
    {
        SimWorld world = World(At("crystal_mine", 10, 4));
        world.Castellan.PlaceAt(new System.Numerics.Vector2(11f, 4f));
        world.Enqueue(new GatherCommand(new GridPos(10, 4)));
        world.Tick();
        Assert.Null(world.Castellan.GatherTarget);
    }

    [Fact]
    public void WellAndMineProduceAtTheirPace()
    {
        SimWorld world = World(Powered($"{At("crystal_mine", 10, 4)}, {At("well", 1, 8)}"),
            """[{ "x": 11, "z": 4 }, { "x": 2, "z": 8 }]""");
        // O poço fica fora da área da torre (10, 6): outra torre a 7 células liga a rede até ele.
        world.Castellan.PlaceAt(new System.Numerics.Vector2(4f, 10f));
        world.Castellan.Inventory.Add("wood", 2);
        world.Castellan.Inventory.Add("pure_shard", 1);
        world.Enqueue(new BuildCommand("mana_tower", new GridPos(3, 6), Direction.North));
        TestWorlds.Run(world, Seconds(40f) + 10);
        Assert.Equal(5, world.BuildingAt(new GridPos(1, 8))!.Machine!.Output.Count("water_jar"));  // 1 a cada 8 s
        Assert.Equal(5, world.BuildingAt(new GridPos(10, 4))!.Machine!.Output.Count("rotten_shard")); // 1 a cada 5 s, cheia em 5
    }
}
