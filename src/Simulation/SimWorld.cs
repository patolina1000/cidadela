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
    public IReadOnlyCollection<Building> Buildings => _buildingByCell.Values;

    /// <summary>Muda a cada construção colocada ou tirada; a cena usa para saber quando redesenhar.</summary>
    public int BuildingsVersion { get; private set; }
    public IReadOnlyList<Villager> Villagers => _villagers;

    private readonly List<ResourceNode> _resources = new();
    private readonly List<Villager> _villagers = new();
    private readonly Dictionary<GridPos, ResourceNode> _resourceByCell = new();
    private readonly Dictionary<GridPos, Building> _buildingByCell = new();
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

    public Building? BuildingAt(GridPos cell) => _buildingByCell.GetValueOrDefault(cell);

    /// <summary>Se a célula bloqueia a passagem (fora do mapa, recurso ou construção sólida).</summary>
    public bool IsSolid(GridPos cell) =>
        !Grid.InBounds(cell) || ResourceAt(cell) is not null || BuildingAt(cell) is { Type.Solid: true };

    /// <summary>Se o Castelão pode construir esse tipo nessa célula agora, e por que não.</summary>
    public BuildCheck CanBuild(BuildingType type, GridPos cell)
    {
        if (!Grid.InBounds(cell))
            return BuildCheck.OutOfBounds;
        if (!Castellan.CanReach(cell))
            return BuildCheck.OutOfReach;
        if (ResourceAt(cell) is not null || BuildingAt(cell) is not null)
            return BuildCheck.Occupied;
        if (type.Solid && Castellan.BodyOverlaps(cell))
            return BuildCheck.Occupied;
        if (!Castellan.Inventory.Has(type.Cost))
            return BuildCheck.NotEnoughItems;
        return BuildCheck.Ok;
    }

    internal void TryBuild(string kind, GridPos cell, Direction direction)
    {
        BuildingType type = Data.Building(kind);
        if (CanBuild(type, cell) != BuildCheck.Ok || !Castellan.Inventory.TryRemove(type.Cost))
            return;
        AddBuilding(type, cell, direction);
    }

    internal void TryDeconstruct(GridPos cell)
    {
        if (BuildingAt(cell) is not Building building || !Castellan.CanReach(cell))
            return;
        _buildingByCell.Remove(cell);
        BuildingsVersion++;
        Castellan.Inventory.Add(building.Type.Cost);
    }

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

    internal Building AddBuilding(BuildingType type, GridPos cell, Direction direction)
    {
        var building = new Building(_nextId++, type, cell, direction);
        _buildingByCell[cell] = building;
        BuildingsVersion++;
        return building;
    }

    internal Villager AddVillager(IReadOnlyList<GridPos> path, float cellsPerSecond)
    {
        var villager = new Villager(_nextId++, path, cellsPerSecond);
        _villagers.Add(villager);
        return villager;
    }
}
