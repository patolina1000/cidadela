using System.Collections.Generic;
using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>
/// Estado completo do jogo. Só muda dentro de <see cref="Tick"/>; a cena apenas lê
/// e manda pedidos pela fila de comandos.
/// </summary>
public sealed class SimWorld
{
    public WorldGrid Grid { get; }
    public GameData Data { get; }
    public long TickCount { get; private set; }
    public Castellan Castellan { get; private set; } = null!;

    public IReadOnlyList<ResourceNode> Resources => _resources;
    public IReadOnlyList<Machine> Machines => _machines;
    public IReadOnlyList<Villager> Villagers => _villagers;

    private readonly List<ResourceNode> _resources = new();
    private readonly List<Machine> _machines = new();
    private readonly List<Villager> _villagers = new();
    private readonly Dictionary<GridPos, ResourceNode> _resourceByCell = new();
    private readonly HashSet<GridPos> _machineCells = new();
    private readonly Queue<ISimCommand> _commands = new();
    private int _nextId = 1;

    public SimWorld(WorldGrid grid, GameData data)
    {
        Grid = grid;
        Data = data;
    }

    /// <summary>Agenda um comando para o próximo tick. Único jeito de a cena mudar o mundo.</summary>
    public void Enqueue(ISimCommand command) => _commands.Enqueue(command);

    public void Tick()
    {
        while (_commands.TryDequeue(out ISimCommand? command))
            command.Apply(this);

        Castellan.Tick(this);
        foreach (Villager villager in _villagers)
            villager.Tick();
        TickCount++;
    }

    /// <summary>Recurso não esgotado naquela célula, ou null.</summary>
    public ResourceNode? ResourceAt(GridPos cell) =>
        _resourceByCell.TryGetValue(cell, out ResourceNode? node) && !node.IsDepleted ? node : null;

    /// <summary>Se a célula bloqueia a passagem (fora do mapa, recurso ou máquina).</summary>
    public bool IsSolid(GridPos cell) =>
        !Grid.InBounds(cell) || ResourceAt(cell) is not null || _machineCells.Contains(cell);

    internal void SetCastellan(Vector2 position)
    {
        Castellan = new Castellan(_nextId++, position, Data.Castellan);
    }

    internal ResourceNode AddResource(string kind, GridPos cell)
    {
        var node = new ResourceNode(_nextId++, Data.Resource(kind), cell);
        _resources.Add(node);
        _resourceByCell[cell] = node;
        return node;
    }

    internal Machine AddMachine(string kind, GridPos cell)
    {
        var machine = new Machine(_nextId++, kind, cell);
        _machines.Add(machine);
        _machineCells.Add(cell);
        return machine;
    }

    internal Villager AddVillager(IReadOnlyList<GridPos> path, float cellsPerSecond)
    {
        var villager = new Villager(_nextId++, path, cellsPerSecond);
        _villagers.Add(villager);
        return villager;
    }
}
