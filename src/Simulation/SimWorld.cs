using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Estado completo do jogo. Só muda dentro de <see cref="Tick"/>; a cena apenas lê.
/// </summary>
public sealed class SimWorld
{
    public WorldGrid Grid { get; }
    public long TickCount { get; private set; }
    public Castellan Castellan { get; private set; } = null!;

    public IReadOnlyList<ResourceNode> Resources => _resources;
    public IReadOnlyList<Machine> Machines => _machines;
    public IReadOnlyList<Villager> Villagers => _villagers;

    private readonly List<ResourceNode> _resources = new();
    private readonly List<Machine> _machines = new();
    private readonly List<Villager> _villagers = new();
    private readonly Queue<ISimCommand> _commands = new();
    private int _nextId = 1;

    public SimWorld(WorldGrid grid)
    {
        Grid = grid;
    }

    /// <summary>Agenda um comando para o próximo tick. Único jeito de a cena mudar o mundo.</summary>
    public void Enqueue(ISimCommand command) => _commands.Enqueue(command);

    public void Tick()
    {
        while (_commands.TryDequeue(out ISimCommand? command))
            command.Apply(this);

        Castellan.Tick(Grid);
        foreach (Villager villager in _villagers)
            villager.Tick();
        TickCount++;
    }

    internal void SetCastellan(System.Numerics.Vector2 position, float cellsPerSecond)
    {
        Castellan = new Castellan(_nextId++, position, cellsPerSecond);
    }

    internal ResourceNode AddResource(string kind, GridPos cell)
    {
        var node = new ResourceNode(_nextId++, kind, cell);
        _resources.Add(node);
        return node;
    }

    internal Machine AddMachine(string kind, GridPos cell)
    {
        var machine = new Machine(_nextId++, kind, cell);
        _machines.Add(machine);
        return machine;
    }

    internal Villager AddVillager(IReadOnlyList<GridPos> path, float cellsPerSecond)
    {
        var villager = new Villager(_nextId++, path, cellsPerSecond);
        _villagers.Add(villager);
        return villager;
    }
}
