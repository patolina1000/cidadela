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
    private readonly List<Building> _machines = new();
    private readonly List<Building> _workplaces = new();
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
        TickMachines();
        foreach (Villager villager in _villagers)
            villager.Tick(this);
        TickWorkplaces();
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
            else if (next?.Machine is MachineState machine && machine.Accepts(lane.Items[0].Kind))
                machine.Input.Add(lane.RemoveFront().Kind);
        }

        foreach (Building belt in _belts)
            foreach (BeltItem item in belt.Belt!.Items)
                item.Position = PositionOnBelt(belt, item.Progress);
    }

    /// <summary>
    /// Cada máquina trabalha e empurra 1 item pronto por tick para a frente: numa esteira que não aponte
    /// de volta para ela, ou num baú.
    /// </summary>
    private void TickMachines()
    {
        foreach (Building building in _machines)
        {
            MachineState machine = building.Machine!;
            machine.Tick();

            if (machine.NextOutput() is string kind && PushForward(building, kind))
                machine.Output.TryRemoveOne(kind);
        }
    }

    /// <summary>Cabana com algo guardado solta 1 item por tick na esteira ou baú à sua frente, como uma máquina.</summary>
    private void TickWorkplaces()
    {
        foreach (Building building in _workplaces)
        {
            Workplace work = building.Workplace!;
            string kind = work.Job.Resource;
            if (work.Stored.Count(kind) > 0 && PushForward(building, kind))
                work.Stored.TryRemoveOne(kind);
        }
    }

    /// <summary>Tenta pôr 1 item na esteira (que não aponte de volta) ou baú à frente da construção.</summary>
    private bool PushForward(Building from, string kind)
    {
        Building? front = BuildingAt(from.Cell.Step(from.Direction));
        if (front?.Belt is BeltLane lane && front.Direction != from.Direction.Opposite() && lane.HasRoomAtEntry)
        {
            var item = new BeltItem(_nextItemId++, kind);
            lane.AddAtEntry(item);
            item.Position = PositionOnBelt(front, 0f);
            item.PreviousPosition = item.Position;
            return true;
        }
        if (front?.Storage is Inventory storage)
        {
            storage.Add(kind);
            return true;
        }
        return false;
    }

    /// <summary>Cada cabana sem trabalhador chama o aldeão livre mais perto dela.</summary>
    internal void AssignIdleWorkers()
    {
        foreach (Building building in _workplaces)
        {
            Workplace work = building.Workplace!;
            if (work.Worker is not null)
                continue;
            var home = new System.Numerics.Vector2(building.Cell.X, building.Cell.Z);
            Villager? nearest = null;
            foreach (Villager v in _villagers)
            {
                if (v.Home is null && (nearest is null ||
                    System.Numerics.Vector2.Distance(v.Position, home) < System.Numerics.Vector2.Distance(nearest.Position, home)))
                    nearest = v;
            }
            if (nearest is null)
                return;
            work.Worker = nearest;
            nearest.AssignHome(building);
        }
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
        else if (target.Machine is MachineState machine && machine.Accepts(kind) && Castellan.Inventory.TryRemoveOne(kind))
        {
            machine.Input.Add(kind);
        }
    }

    internal void TryTakeAll(GridPos cell)
    {
        if (BuildingAt(cell) is not Building building || !Castellan.CanReach(cell))
            return;
        building.Storage?.MoveAllTo(Castellan.Inventory);
        building.Machine?.Output.MoveAllTo(Castellan.Inventory);
        building.Workplace?.Stored.MoveAllTo(Castellan.Inventory);
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
        _machines.Remove(building);
        _workplaces.Remove(building);
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
        building.Machine?.EmptyInto(Castellan.Inventory);
        if (building.Workplace is Workplace work)
        {
            work.Stored.MoveAllTo(Castellan.Inventory);
            work.Worker?.DropCarryInto(Castellan.Inventory);
            work.Worker?.AssignHome(null);
            work.Worker = null;
            AssignIdleWorkers(); // o aldeão liberado pode ir para outra cabana vazia
        }
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
        var building = new Building(_nextId++, type, cell, direction, Data.RecipeFor(type.Kind));
        _buildingByCell[cell] = building;
        if (building.Belt is not null)
            _belts.Add(building);
        if (building.Machine is not null)
            _machines.Add(building);
        if (building.Workplace is not null)
        {
            _workplaces.Add(building);
            AssignIdleWorkers();
        }
        BuildingsVersion++;
        return building;
    }

    internal Villager AddVillager(System.Numerics.Vector2 position)
    {
        var villager = new Villager(_nextId++, position, Data.Villagers);
        _villagers.Add(villager);
        return villager;
    }
}
