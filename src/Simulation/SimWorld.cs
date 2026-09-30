using System;
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

    /// <summary>Vitrine (palco da Biografia): máquinas andam sem gente nos postos. O jogo nunca liga.</summary>
    public bool FreeMachines { get; internal set; }

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
    /// <summary>Construções que chamam aldeões (cabanas e postos), na ordem em que foram construídas.</summary>
    private readonly List<Building> _staffed = new();
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
            machine.CrewReady = FreeMachines || building.CrewReady;
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

    /// <summary>
    /// Tenta pôr 1 item na esteira (que não aponte de volta) ou baú à frente da construção. Item pesado não entra em
    /// esteira: só no baú.
    /// </summary>
    private bool PushForward(Building from, string kind)
    {
        Building? front = BuildingAt(from.Cell.Step(from.Direction));
        if (front?.Belt is BeltLane lane && front.Direction != from.Direction.Opposite() && lane.HasRoomAtEntry && !IsHeavy(kind))
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

    /// <summary>
    /// Cada cabana sem trabalhador e cada posto vago chama o aldeão livre mais perto, na ordem em que as construções
    /// foram feitas (quem construiu primeiro é atendido primeiro).
    /// </summary>
    internal void AssignIdleWorkers()
    {
        foreach (Building building in _staffed)
        {
            if (building.Workplace is Workplace work)
            {
                if (work.Worker is not null)
                    continue;
                if (NearestIdle(building) is not Villager worker)
                    return;
                work.Worker = worker;
                worker.AssignHome(building);
                continue;
            }
            for (int i = 0; i < building.Crew.Length; i++)
            {
                if (building.Crew[i] is not null)
                    continue;
                if (NearestIdle(building) is not Villager crew)
                    return;
                building.Crew[i] = crew;
                crew.AssignHome(building);
            }
        }
    }

    private Villager? NearestIdle(Building building)
    {
        var home = new System.Numerics.Vector2(building.Cell.X, building.Cell.Z);
        Villager? nearest = null;
        foreach (Villager v in _villagers)
        {
            if (v.Home is null && (nearest is null ||
                System.Numerics.Vector2.Distance(v.Position, home) < System.Numerics.Vector2.Distance(nearest.Position, home)))
                nearest = v;
        }
        return nearest;
    }

    private static System.Numerics.Vector2 PositionOnBelt(Building belt, float progress) =>
        new System.Numerics.Vector2(belt.Cell.X, belt.Cell.Z) + belt.Direction.ToVector() * (progress - 0.5f);

    internal void TryInsertItem(GridPos cell, string kind)
    {
        if (BuildingAt(cell) is not Building target || !Castellan.CanReach(cell))
            return;

        if (target.Belt is BeltLane lane && lane.HasRoomAtEntry && !IsHeavy(kind) && Castellan.Inventory.TryRemoveOne(kind))
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

    /// <summary>Se o item é pesado (não entra em esteira nem em mariposa; só nas costas).</summary>
    public bool IsHeavy(string kind) => Data.Item(kind).IsHeavy;

    /// <summary>
    /// Item nascendo na entrada de uma esteira (alimentador do palco da Biografia e de testes). Não olha a regra do
    /// peso: é um alimentador de cena, não o jogo.
    /// </summary>
    internal void TrySpawnItem(GridPos cell, string kind)
    {
        if (BuildingAt(cell) is not { Belt: BeltLane lane } target || !lane.HasRoomAtEntry)
            return;
        var item = new BeltItem(_nextItemId++, kind);
        lane.AddAtEntry(item);
        item.Position = PositionOnBelt(target, 0f);
        item.PreviousPosition = item.Position;
    }

    internal void TryTakeAll(GridPos cell)
    {
        if (BuildingAt(cell) is not Building building || !Castellan.CanReach(cell))
            return;
        building.Storage?.MoveAllTo(Castellan.Inventory);
        building.Machine?.Output.MoveAllTo(Castellan.Inventory);
        building.Workplace?.Stored.MoveAllTo(Castellan.Inventory);
    }

    /// <summary>
    /// Multiplicador de velocidade do piso na célula (GDD, pisos construídos): a construção não sólida que
    /// estiver ali com "speedBonus"; 1 sem piso. Os pisos construídos ainda não existem; o gancho já vale.
    /// </summary>
    public float FloorBonusAt(GridPos cell) => BuildingAt(cell) is { Type.Solid: false } floor ? floor.Type.SpeedBonus : 1f;

    /// <summary>Recurso não esgotado naquela célula, ou null.</summary>
    public ResourceNode? ResourceAt(GridPos cell) =>
        _resourceByCell.TryGetValue(cell, out ResourceNode? node) && !node.IsDepleted ? node : null;

    public Building? BuildingAt(GridPos cell) => _buildingByCell.GetValueOrDefault(cell);

    /// <summary>Se a célula bloqueia a passagem (fora do mapa, recurso ou construção sólida).</summary>
    /// <summary>Forma que o recurso da célula bloqueia (tronco, base da pedra ou do veio), ou null.</summary>
    public ResourceShape? ShapeAt(GridPos cell) => ResourceAt(cell)?.Shape;

    /// <summary>
    /// Se a célula bloqueia o caminho dos aldeões: como <see cref="IsSolid"/>, menos a célula de recurso que só bloqueia um
    /// círculo (o aldeão passa sob a copa ou rente à pedra, desviando do círculo ao andar).
    /// </summary>
    public bool BlocksVillager(GridPos cell) => IsSolid(cell) && ShapeAt(cell) is null;

    /// <summary>
    /// Empurra um corpo (posição no centro de célula, como a do Castelão e a dos aldeões) para fora dos círculos dos
    /// recursos em volta (troncos, pedras, veios): quem anda contra um desliza em volta dele, em vez de parar. Poucas
    /// passadas bastam para dois vizinhos.
    /// </summary>
    /// <summary>A forma de recurso mais perto de um corpo (a menos de <paramref name="within"/> da borda), e o centro da célula dela.</summary>
    public (ResourceShape Shape, Vector2 Center)? NearestShape(Vector2 position, float within)
    {
        (ResourceShape, Vector2)? best = null;
        float bestDistance = within;
        int cx = (int)MathF.Round(position.X), cz = (int)MathF.Round(position.Y);
        for (int dx = -1; dx <= 1; dx++)
        for (int dz = -1; dz <= 1; dz++)
        {
            var cell = new GridPos(cx + dx, cz + dz);
            if (ShapeAt(cell) is ResourceShape shape && shape.SignedDistance(position) is float d && d < bestDistance)
            {
                bestDistance = d;
                best = (shape, new Vector2(cell.X, cell.Z));
            }
        }
        return best;
    }

    /// <summary>Se o corpo invade o círculo de algum recurso em volta (sobra de empurrão entre dois vizinhos apertados).</summary>
    public bool OverlapsResourceCircle(Vector2 position, float radius)
    {
        int cx = (int)MathF.Round(position.X), cz = (int)MathF.Round(position.Y);
        for (int dx = -1; dx <= 1; dx++)
        for (int dz = -1; dz <= 1; dz++)
        {
            var cell = new GridPos(cx + dx, cz + dz);
            if (ShapeAt(cell) is ResourceShape shape && shape.SignedDistance(position) < radius - 0.001f)
                return true;
        }
        return false;
    }

    public Vector2 PushOutOfTrunks(Vector2 position, float radius)
    {
        for (int pass = 0; pass < 3; pass++)
        {
            bool moved = false;
            int cx = (int)MathF.Round(position.X), cz = (int)MathF.Round(position.Y);
            for (int dx = -1; dx <= 1; dx++)
            for (int dz = -1; dz <= 1; dz++)
            {
                var cell = new GridPos(cx + dx, cz + dz);
                if (ShapeAt(cell) is not ResourceShape shape)
                    continue;
                Vector2 pushed = shape.PushOut(position, radius);
                if (pushed == position)
                    continue;
                position = pushed;
                moved = true;
            }
            if (!moved)
                break;
        }
        return position;
    }

    public bool IsSolid(GridPos cell) =>
        !Grid.InBounds(cell) || IsWater(cell) || ResourceAt(cell) is not null || BuildingAt(cell) is { Type.Solid: true };

    /// <summary>Se a célula é água (rio, lago): ninguém passa e nada se constrói nela.</summary>
    public bool IsWater(GridPos cell) => Grid.InBounds(cell) && Data.Terrains[Grid.TerrainAt(cell)].Water;

    /// <summary>Se o Castelão pode construir esse tipo nessa célula agora, e por que não.</summary>
    public BuildCheck CanBuild(BuildingType type, GridPos cell)
    {
        if (!Grid.InBounds(cell))
            return BuildCheck.OutOfBounds;
        if (!Castellan.CanReach(cell))
            return BuildCheck.OutOfReach;
        if (ResourceAt(cell) is not null || BuildingAt(cell) is not null)
            return BuildCheck.Occupied;
        if (IsWater(cell))
            return BuildCheck.WrongGround;
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
        _staffed.Remove(building);
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
        if (building.Crew.Length > 0)
        {
            for (int i = 0; i < building.Crew.Length; i++)
            {
                building.Crew[i]?.DropCarryInto(Castellan.Inventory); // carregador com carga na mão
                building.Crew[i]?.AssignHome(null);
                building.Crew[i] = null;
            }
            AssignIdleWorkers(); // quem saiu do posto pode ir para outro vago
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
            _workplaces.Add(building);
        BuildingsVersion++;
        if (building.Workplace is not null || building.Crew.Length > 0)
        {
            _staffed.Add(building);
            AssignIdleWorkers();
        }
        return building;
    }

    internal Villager AddVillager(System.Numerics.Vector2 position)
    {
        var villager = new Villager(_nextId++, position, Data.Villagers);
        _villagers.Add(villager);
        return villager;
    }
}
