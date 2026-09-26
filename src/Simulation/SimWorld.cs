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
    private readonly List<Building> _belts = new();
    private int _nextItemId = 1;
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
        TickBelts();
        foreach (Villager villager in _villagers)
            villager.Tick();
        TickCount++;
    }

    /// <summary>Todos os itens em esteiras agora, para a cena desenhar.</summary>
    public IEnumerable<BeltItem> BeltItems
    {
        get
        {
            foreach (Building belt in _belts)
                foreach (BeltItem item in belt.Belt!.Items)
                    yield return item;
        }
    }

    /// <summary>
    /// Duas fases: primeiro todos andam dentro da própria esteira; depois quem chegou na saída tenta
    /// passar para a esteira (ou baú) à frente. Esteira de frente contra esta não aceita.
    /// </summary>
    private void TickBelts()
    {
        foreach (Building belt in _belts)
            foreach (BeltItem item in belt.Belt!.Items)
                item.PreviousPosition = item.Position;

        foreach (Building belt in _belts)
            belt.Belt!.Advance(belt.Type.BeltSpeed / SimClock.TicksPerSecond);

        foreach (Building belt in _belts)
        {
            BeltLane lane = belt.Belt!;
            if (lane.Items.Count == 0 || lane.Items[0].Progress < 1f)
                continue;

            Building? next = BuildingAt(belt.Cell.Step(belt.Direction));
            if (next?.Belt is BeltLane nextLane && next.Direction != belt.Direction.Opposite() && nextLane.HasRoomAtEntry)
                nextLane.AddAtEntry(lane.RemoveFront());
            else if (next?.Storage is Inventory storage)
                storage.Add(lane.RemoveFront().Kind);
        }

        foreach (Building belt in _belts)
            foreach (BeltItem item in belt.Belt!.Items)
                item.Position = PositionOnBelt(belt, item.Progress);
    }

    private static System.Numerics.Vector2 PositionOnBelt(Building belt, float progress) =>
        new System.Numerics.Vector2(belt.Cell.X, belt.Cell.Z) + belt.Direction.ToVector() * (progress - 0.5f);

    internal void TryInsertItem(GridPos cell, string kind)
    {
        if (BuildingAt(cell) is not Building target || !Castellan.CanReach(cell))
            return;

        if (target.Belt is BeltLane lane && lane.HasRoomAtEntry && Castellan.Inventory.TryRemoveOne(kind))
        {
            var item = new BeltItem(_nextItemId++, kind);
            lane.AddAtEntry(item);
            item.Position = PositionOnBelt(target, 0f);
            item.PreviousPosition = item.Position;
        }
        else if (target.Storage is Inventory storage && Castellan.Inventory.TryRemoveOne(kind))
        {
            storage.Add(kind);
        }
    }

    internal void TryTakeFromChest(GridPos cell)
    {
        if (BuildingAt(cell)?.Storage is Inventory storage && Castellan.CanReach(cell))
            storage.MoveAllTo(Castellan.Inventory);
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
        _belts.Remove(building);
        BuildingsVersion++;
        Castellan.Inventory.Add(building.Type.Cost);
        // O que estava em cima ou dentro volta junto.
        if (building.Belt is BeltLane lane)
        {
            foreach (BeltItem item in lane.Items)
                Castellan.Inventory.Add(item.Kind);
            lane.Clear();
        }
        building.Storage?.MoveAllTo(Castellan.Inventory);
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
        if (building.Belt is not null)
            _belts.Add(building);
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
