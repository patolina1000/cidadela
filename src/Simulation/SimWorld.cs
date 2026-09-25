using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Estado completo do jogo. Só muda dentro de <see cref="Tick"/>; a cena apenas lê.
/// </summary>
public sealed class SimWorld
{
    public WorldGrid Grid { get; }
    public long TickCount { get; private set; }

    public IReadOnlyList<ResourceNode> Resources => _resources;
    public IReadOnlyList<Machine> Machines => _machines;
    public IReadOnlyList<Villager> Villagers => _villagers;

    private readonly List<ResourceNode> _resources = new();
    private readonly List<Machine> _machines = new();
    private readonly List<Villager> _villagers = new();
    private int _nextId = 1;

    public SimWorld(WorldGrid grid)
    {
        Grid = grid;
    }

    public void Tick()
    {
        foreach (Villager villager in _villagers)
            villager.Tick();
        TickCount++;
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
