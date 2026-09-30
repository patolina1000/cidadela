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

    /// <summary>Vitrine (palco da Biografia): máquinas andam sem gente nos postos e a saída some. O jogo nunca liga.</summary>
    public bool FreeMachines { get; internal set; }

    /// <summary>As redes de mana atuais (refeitas só quando uma construção entra ou sai).</summary>
    public IReadOnlyList<ManaNetwork> ManaNetworks => _networks;

    /// <summary>Quantas vezes as redes de mana foram refeitas (testes: só quando algo muda).</summary>
    public int ManaRebuilds { get; private set; }

    /// <summary>Muda a cada construção colocada ou tirada; a cena usa para saber quando redesenhar.</summary>
    public int BuildingsVersion { get; private set; }
    public IReadOnlyList<Villager> Villagers => _villagers;

    private readonly List<ResourceNode> _resources = new();
    private readonly List<Villager> _villagers = new();
    private readonly Dictionary<GridPos, ResourceNode> _resourceByCell = new();
    private readonly Dictionary<GridPos, Building> _buildingByCell = new();
    private readonly List<Building> _machines = new();
    private readonly List<Building> _workplaces = new();
    /// <summary>Construções que chamam aldeões (cabanas e postos), na ordem em que foram construídas.</summary>
    private readonly List<Building> _staffed = new();
    private readonly List<ManaNetwork> _networks = new();
    private int _networksVersion = -1;
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
        Building? postBefore = Castellan.Post;
        while (_commands.TryDequeue(out ISimCommand? command))
            command.Apply(this);

        Castellan.Tick(this);
        if (postBefore is not null && Castellan.Post != postBefore && _buildingByCell.ContainsValue(postBefore))
            AssignIdleWorkers(); // ela saiu do posto: um aldeão livre pode ocupar
        UpdateMana();
        TickMachines();
        foreach (Villager villager in _villagers)
            villager.Tick(this);
        TickWorkplaces();
        TickCount++;
    }

    /// <summary>
    /// Cada máquina trabalha na fração de mana da rede. Nunca solta nada sozinha: a saída fica guardada até uma mariposa
    /// ou alguém tirar (docs/linha_energia.md, regra 4; D6 do Arthur). A mina tira 1 do veio a cada ciclo que começa.
    /// </summary>
    private void TickMachines()
    {
        foreach (Building building in _machines)
        {
            MachineState machine = building.Machine!;
            machine.Exhausted = building.Source is { IsDepleted: true };
            if (building.Type.SpawnsVillager)
            {
                if (building.PendingVillagers > 0 && FreeCellBeside(building.Cell) is GridPos spawn)
                    SpawnVillager(building, spawn);
                machine.NoRoom = building.PendingVillagers > 0;
            }
            machine.Tick(building.ManaSatisfaction);
            if (FreeMachines)
                machine.Output.MoveAllTo(new Inventory()); // vitrine da Biografia: a saída some, a máquina segue
            if (machine.StartedThisTick)
                building.Source?.TakeOne();
            if (machine.CompletedThisTick && building.Type.SpawnsVillager)
            {
                building.PendingVillagers++;
                if (FreeCellBeside(building.Cell) is GridPos cell)
                    SpawnVillager(building, cell);
            }
        }
    }

    /// <summary>
    /// Mana (docs/linha_energia.md, regra 6): refaz as redes se alguma construção mudou; soma o que cada rede gera e o que
    /// os consumidores pedem neste tick (máquina só pede trabalhando ou prestes a começar: D1 do Arthur, 30/09). A sobra
    /// se perde.
    /// </summary>
    private void UpdateMana()
    {
        if (_networksVersion != BuildingsVersion)
            RebuildManaNetworks();
        foreach (Building building in _machines)
            building.Machine!.CrewReady = FreeMachines || building.CrewReady;
        foreach (ManaNetwork network in _networks)
        {
            float supply = 0f, demand = 0f;
            foreach (Building b in network.Members)
            {
                b.ManaSupply = SupplyOf(b);
                b.ManaDemand = DemandOf(b);
                supply += b.ManaSupply;
                demand += b.ManaDemand;
            }
            network.Supply = supply;
            network.Demand = demand;
        }
    }

    /// <summary>
    /// Gerador: com receita (o Relicário, que queima combustível), enquanto queima ou tem o que começar a queimar (sem buraco
    /// no tick entre dois ciclos); sem receita, sempre.
    /// </summary>
    private static float SupplyOf(Building b) =>
        b.Type.Mana is not { Supply: > 0f } mana ? 0f
        : b.Machine is null || b.Machine.IsWorking || b.Machine.CanStart ? mana.Supply : 0f;

    /// <summary>
    /// Consumidor: máquina só trabalhando ou prestes a começar (com gente no posto); sem receita, sempre.
    /// </summary>
    private static float DemandOf(Building b)
    {
        if (b.Type.Mana is not { Use: > 0f } mana)
            return 0f;
        if (b.Machine is not MachineState m)
            return mana.Use;
        return m.CrewReady && (m.IsWorking || m.CanStart) ? mana.Use : 0f;
    }

    /// <summary>
    /// Refaz as redes de mana: torres se ligam às outras ao alcance do fio (o menor dos dois), e cada construção dentro
    /// da área de uma torre entra na rede dela (a da primeira torre construída, se estiver em duas). Só roda quando uma
    /// construção entra ou sai.
    /// </summary>
    private void RebuildManaNetworks()
    {
        _networksVersion = BuildingsVersion;
        ManaRebuilds++;
        _networks.Clear();
        var towers = new List<Building>();
        foreach (Building b in _buildingByCell.Values)
        {
            b.Network = null;
            if (b.Type.Tower is not null)
                towers.Add(b);
        }
        towers.Sort((a, b) => a.Id.CompareTo(b.Id));
        foreach (Building start in towers)
        {
            if (start.Network is not null)
                continue;
            var network = new ManaNetwork();
            var queue = new Queue<Building>();
            start.Network = network;
            queue.Enqueue(start);
            while (queue.TryDequeue(out Building? t))
            {
                network.Towers.Add(t);
                foreach (Building other in towers)
                    if (other.Network is null && WireReaches(t, other))
                    {
                        other.Network = network;
                        queue.Enqueue(other);
                    }
            }
            _networks.Add(network);
        }
        foreach (ManaNetwork network in _networks)
            network.Members.AddRange(network.Towers);
        foreach (Building b in _buildingByCell.Values)
        {
            if (b.Network is not null || b.Type.Mana is null)
                continue;
            foreach (Building t in towers)
            {
                int half = t.Type.Tower!.Area / 2;
                if (Math.Abs(b.Cell.X - t.Cell.X) <= half && Math.Abs(b.Cell.Z - t.Cell.Z) <= half)
                {
                    b.Network = t.Network;
                    t.Network!.Members.Add(b);
                    break;
                }
            }
        }
        foreach (Building b in _buildingByCell.Values)
            if (b.Network is null)
                b.ManaSupply = b.ManaDemand = 0f;
    }

    private static bool WireReaches(Building a, Building b)
    {
        float reach = MathF.Min(a.Type.Tower!.Wire, b.Type.Tower!.Wire);
        float dx = a.Cell.X - b.Cell.X, dz = a.Cell.Z - b.Cell.Z;
        return dx * dx + dz * dz <= reach * reach + 1e-4f;
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
    /// Tenta pôr 1 item na esteira (que não aponte de volta) ou baú à frente da cabana. Item pesado não entra em
    /// esteira: só no baú.
    /// </summary>
    private bool PushForward(Building from, string kind)
    {
        Building? front = BuildingAt(from.Cell.Step(from.Direction));
        if (front?.Storage is Inventory storage)
        {
            storage.Add(kind);
            return true;
        }
        return false;
    }

    /// <summary>
    /// O aldeão formado nasce VAZIO na célula ao lado e fica parado ali, sem ir para posto nenhum, até receber uma
    /// ladainha (docs/ladainhas.md; substitui o "vai sozinho para o posto vazio").
    /// </summary>
    private void SpawnVillager(Building from, GridPos cell)
    {
        from.PendingVillagers--;
        from.VillagersFormed++;
        from.LastFormedTick = TickCount;
        AddVillager(new Vector2(cell.X, cell.Z)).Blank = true;
    }

    /// <summary>Uma célula livre encostada (de lado primeiro, depois na diagonal), ou null (L5 do Arthur).</summary>
    private GridPos? FreeCellBeside(GridPos cell)
    {
        foreach (Direction d in DirectionExtensions.All)
            if (!IsSolid(cell.Step(d)))
                return cell.Step(d);
        for (int dx = -1; dx <= 1; dx += 2)
        for (int dz = -1; dz <= 1; dz += 2)
        {
            var diagonal = new GridPos(cell.X + dx, cell.Z + dz);
            if (!IsSolid(diagonal))
                return diagonal;
        }
        return null;
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
                if (building.Crew[i] is not null || building.CastellanSlot == i)
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
            if (v.Home is null && !v.Blank && (nearest is null ||
                System.Numerics.Vector2.Distance(v.Position, home) < System.Numerics.Vector2.Distance(nearest.Position, home)))
                nearest = v;
        }
        return nearest;
    }

    internal void TryInsertItem(GridPos cell, string kind)
    {
        if (BuildingAt(cell) is not Building target || !Castellan.CanReach(cell))
            return;

        if (target.Storage is Inventory storage && Castellan.Inventory.TryRemoveOne(kind))
        {
            storage.Add(kind);
        }
        else if (target.Machine is MachineState machine && machine.Accepts(kind) && Castellan.Inventory.TryRemoveOne(kind))
        {
            machine.Input.Add(kind);
        }
    }

    /// <summary>Se o item é pesado (carga por viagem: 1 por ponto de Força; o leve vai de 10 em 10).</summary>
    public bool IsHeavy(string kind) => Data.Item(kind).IsHeavy;

    /// <summary>
    /// Item posto direto na entrada da máquina (se ela aceita) ou no baú da célula, sem Castelão nem alcance: alimentador
    /// da vitrine da Biografia e de testes. Não é o jogo.
    /// </summary>
    internal void TrySpawnItem(GridPos cell, string kind)
    {
        if (BuildingAt(cell) is { Machine: MachineState machine } && machine.Accepts(kind))
            machine.Input.Add(kind);
        else if (BuildingAt(cell)?.Storage is Inventory storage)
            storage.Add(kind);
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
    /// <summary>
    /// Forma que o recurso da célula bloqueia (tronco, base da pedra ou do veio), ou null. Com uma construção em cima (a
    /// mina sobre o veio), a célula inteira bloqueia: null.
    /// </summary>
    public ResourceShape? ShapeAt(GridPos cell) => BuildingAt(cell) is null ? ResourceAt(cell)?.Shape : null;

    /// <summary>Recurso que se pode coletar à mão ou por cabana: sem construção em cima.</summary>
    public ResourceNode? GatherableAt(GridPos cell) => BuildingAt(cell) is null ? ResourceAt(cell) : null;

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
        if (BuildingAt(cell) is not null)
            return BuildCheck.Occupied;
        ResourceNode? resource = ResourceAt(cell);
        if (type.OnResource is string needed)
        {
            if (resource?.Kind != needed)
                return BuildCheck.WrongGround;
        }
        else if (resource is not null)
            return BuildCheck.Occupied;
        if (IsWater(cell) || (type.NextToWater && !TouchesWater(cell)) || (type.OnBank && !IsBank(cell)))
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
        if (BuildingAt(cell) is not Building building || building.Type.Fixed || !Castellan.CanReach(cell))
            return;
        if (Castellan.Post == building)
            Castellan.LeavePost();
        _buildingByCell.Remove(cell);
        _machines.Remove(building);
        _workplaces.Remove(building);
        _staffed.Remove(building);
        BuildingsVersion++;
        Castellan.Inventory.Add(building.Type.Cost);
        // O que estava dentro volta junto.
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

    /// <summary>
    /// E (docs/linha_energia.md): se ela está num posto, sai; senão assume um posto vago da máquina encostada nela (a mais
    /// perto, de lado ou na diagonal). Posto com aldeão designado (mesmo a caminho) não é vago.
    /// </summary>
    internal void ToggleCastellanPost()
    {
        if (Castellan.Post is not null)
        {
            Castellan.LeavePost();
            return;
        }
        Building? best = null;
        int bestSlot = -1;
        float bestDistance = float.MaxValue;
        int cx = (int)MathF.Round(Castellan.Position.X), cz = (int)MathF.Round(Castellan.Position.Y);
        for (int dx = -2; dx <= 2; dx++)
        for (int dz = -2; dz <= 2; dz++)
        {
            var cell = new GridPos(cx + dx, cz + dz);
            if (BuildingAt(cell) is not { Type.Posts: not null } b || !Castellan.CanGather(cell))
                continue;
            int slot = Array.IndexOf(b.Crew, null);
            float distance = Vector2.Distance(Castellan.Position, new Vector2(cell.X, cell.Z));
            if (slot >= 0 && b.CastellanSlot is null && distance < bestDistance)
            {
                best = b;
                bestSlot = slot;
                bestDistance = distance;
            }
        }
        if (best is not null)
            Castellan.TakePost(best, bestSlot);
    }

    /// <summary>Se a célula é margem (terra encostada na água, onde se cava argila; docs/linha_aldeoes.md).</summary>
    public bool IsBank(GridPos cell) => Grid.InBounds(cell) && Data.Terrains[Grid.TerrainAt(cell)].Bank;

    /// <summary>Se alguma das 4 vizinhas é água (o poço fica de lado para ela).</summary>
    public bool TouchesWater(GridPos cell)
    {
        foreach (Direction d in DirectionExtensions.All)
            if (IsWater(cell.Step(d)))
                return true;
        return false;
    }

    internal Building AddBuilding(BuildingType type, GridPos cell, Direction direction)
    {
        var building = new Building(_nextId++, type, cell, direction, Data.RecipeFor(type.Kind));
        if (type.OnResource is not null)
            building.Source = _resourceByCell.GetValueOrDefault(cell);
        _buildingByCell[cell] = building;
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
