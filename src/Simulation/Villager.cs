using System;
using System.Collections.Generic;
using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>O que o aldeão está fazendo agora.</summary>
public enum VillagerTask
{
    /// <summary>Sem cabana: parado esperando trabalho.</summary>
    Unemployed,
    /// <summary>Tem cabana, mas não achou recurso alcançável (ou a cabana está cheia).</summary>
    Waiting,
    GoingToResource,
    Gathering,
    ReturningHome,
    /// <summary>Chamado para um posto de máquina: andando até encostar nela.</summary>
    GoingToPost,
    /// <summary>Encostado na máquina, no posto: conta para a equipe dela.</summary>
    AtPost,
    /// <summary>Carregador indo buscar bruto num baú ou cabana.</summary>
    Fetching,
    /// <summary>Carregador levando bruto até a máquina.</summary>
    Hauling,
}

/// <summary>
/// Aldeão trabalhador (GDD, seção 6). Com uma cabana, repete sozinho: acha o recurso do ofício mais
/// perto dentro do raio, anda até encostar (caminho A*), coleta até encher a carga e volta para entregar.
/// Aldeões não colidem entre si nem com o Castelão. A célula de árvore não bloqueia o caminho (só o tronco): eles passam
/// sob a copa, deslizando em volta do tronco, e coletam encostados nele.
/// </summary>
public sealed class Villager
{
    private const int RetryTicks = SimClock.TicksPerSecond;
    /// <summary>Ocioso por este tempo, fica sonolento.</summary>
    public const int SleepyAfterTicks = 30 * SimClock.TicksPerSecond;
    /// <summary>Quanto tempo a alegria de uma entrega dura.</summary>
    public const int HappyTicks = 3 * SimClock.TicksPerSecond;
    /// <summary>Quantas variações de cabelo existem (data/villager_looks.json lista as peças).</summary>
    public const int HairVariants = 5;

    public int Id { get; }
    public VillagerStats Stats { get; }

    /// <summary>Variação de cabelo, 1 a <see cref="HairVariants"/>, sorteada ao nascer (fixa pelo id).</summary>
    public int HairVariant { get; }

    /// <summary>Expressão do rosto neste tick, pelas regras do GDD (tabela de expressões).</summary>
    public VillagerExpression Expression { get; private set; } = VillagerExpression.Distracted;

    /// <summary>Descansando (dormindo). Ainda não há noite na simulação; quem for criar a noite liga isto.</summary>
    public bool Resting { get; private set; }

    /// <summary>Patamar de velocidade (índice em <see cref="VillagerStats.SpeedTiers"/>): 0 = base; as melhorias sobem.</summary>
    public int SpeedTier { get; private set; }

    /// <summary>Com fome ou moral baixa: a velocidade cai pela penalidade. Os dois estados ainda não existem; quem os criar liga isto.</summary>
    public bool Penalized { get; private set; }

    /// <summary>
    /// Velocidade final neste tick, em células por segundo: patamar × bônus do piso da célula × penalidade,
    /// presa ao teto (decisão de 29/09/2026). A view lê para a animação acompanhar (os pés não deslizam).
    /// </summary>
    public float Speed { get; private set; }

    /// <summary>Posição contínua no plano da grade (X, Z), em células; (x, z) = centro da célula x, z.</summary>
    public Vector2 Position { get; private set; }

    /// <summary>Posição no tick anterior, para a cena interpolar.</summary>
    public Vector2 PreviousPosition { get; private set; }

    public Vector2 Facing { get; private set; } = new(0f, 1f);
    public Building? Home { get; private set; }
    public VillagerTask Task { get; private set; } = VillagerTask.Unemployed;

    /// <summary>
    /// Estado para o ícone, do mais forte para o mais fraco: descansando, sem trabalho, cabana cheia, sem caminho,
    /// sem recurso no raio, e então o que está fazendo (coletando, levando a carga, indo, esperando).
    /// </summary>
    public VillagerStatus Status =>
        Resting ? VillagerStatus.Resting
        : Home is null ? VillagerStatus.Unemployed
        : Task == VillagerTask.AtPost ? VillagerStatus.AtPost
        : Task == VillagerTask.Fetching ? VillagerStatus.Fetching
        : Task == VillagerTask.Hauling ? VillagerStatus.Hauling
        : Home.Workplace is null && _noPath ? VillagerStatus.NoPath
        : Home.Type.Carriers is not null ? VillagerStatus.NothingToHaul
        : Task == VillagerTask.GoingToPost || Home.Workplace is null ? VillagerStatus.GoingToPost
        : _hutFull ? VillagerStatus.HutFull
        : _noPath ? VillagerStatus.NoPath
        : _noResource ? VillagerStatus.NoResource
        : Task switch
        {
            VillagerTask.Gathering => VillagerStatus.Gathering,
            VillagerTask.ReturningHome => VillagerStatus.Carrying,
            VillagerTask.GoingToResource => VillagerStatus.GoingToResource,
            _ => VillagerStatus.Waiting,
        };
    public ResourceNode? Target { get; private set; }
    public string? CarryingKind { get; private set; }
    public int CarryingCount { get; private set; }

    /// <summary>Progresso do item sendo coletado, de 0 a 1.</summary>
    public float GatherProgress => Target is null || Task != VillagerTask.Gathering ? 0f : (float)_gatherTicks / GatherTicksFor(Target);

    public GridPos Cell => new((int)MathF.Round(Position.X), (int)MathF.Round(Position.Y));

    /// <summary>Ferramenta do posto em que está trabalhando (para o ícone sobre a cabeça), ou null fora do posto.</summary>
    public string? PostTool => Task == VillagerTask.AtPost ? Home?.Type.Posts?.Tool : null;

    /// <summary>Célula onde fica encostado no posto (escolhida ao ir), ou null.</summary>
    public GridPos? PostCell { get; private set; }

    /// <summary>Carregador: de onde está buscando (baú ou cabana), ou null.</summary>
    public Building? HaulFrom { get; private set; }

    /// <summary>Carregador: a máquina para onde leva, ou null.</summary>
    public Building? HaulTo { get; private set; }

    /// <summary>Carregador: o item e quantos ele leva (ou vai buscar) para <see cref="HaulTo"/>; conta como já a caminho.</summary>
    public string? HaulKind { get; private set; }
    public int HaulAmount { get; private set; }

    private readonly Queue<GridPos> _path = new();
    private int _gatherTicks;
    private int _retryIn;
    private int _idleTicks;
    private int _happyTicks;
    private bool _hutFull;
    private bool _noPath;
    private bool _noResource;

    public Villager(int id, Vector2 position, VillagerStats stats)
    {
        Id = id;
        Position = position;
        PreviousPosition = position;
        Stats = stats;
        Speed = stats.BaseSpeed;
        // Mistura simples do id: aldeões vizinhos não saem com cabelos em sequência.
        HairVariant = 1 + (int)(((uint)id * 2654435761u >> 16) % HairVariants);
    }

    /// <summary>Liga ou desliga o descanso (o sistema de noite, quando existir, chama isto).</summary>
    public void SetResting(bool resting) => Resting = resting;

    /// <summary>Muda o patamar de velocidade (pesquisa ou era, quando existirem; hoje a tecla de depuração). Fora da lista, prende nas pontas.</summary>
    public void SetSpeedTier(int tier) => SpeedTier = Math.Clamp(tier, 0, Stats.SpeedTiers.Count - 1);

    /// <summary>Liga ou desliga a penalidade de velocidade (fome ou moral baixa, quando existirem).</summary>
    public void SetPenalized(bool penalized) => Penalized = penalized;

    internal void AssignHome(Building? home)
    {
        Home = home;
        Target = null;
        _path.Clear();
        _gatherTicks = 0;
        _retryIn = 0;
        _hutFull = false;
        _noPath = false;
        _noResource = false;
        _idleTicks = 0;
        PostCell = null;
        HaulFrom = HaulTo = null;
        HaulKind = null;
        HaulAmount = 0;
        Task = home is null ? VillagerTask.Unemployed : VillagerTask.Waiting;
    }

    /// <summary>Esvazia a carga (a cabana sumiu: os itens vão para quem desmontou).</summary>
    internal void DropCarryInto(Inventory target)
    {
        if (CarryingKind is string kind && CarryingCount > 0)
            target.Add(kind, CarryingCount);
        CarryingKind = null;
        CarryingCount = 0;
    }

    internal void Tick(SimWorld world)
    {
        PreviousPosition = Position;
        Speed = Stats.FinalSpeed(SpeedTier, world.FloorBonusAt(Cell), Penalized);
        if (_happyTicks > 0)
            _happyTicks--;
        if (Home is null)
        {
            _idleTicks++;
            UpdateExpression();
            return;
        }
        if (Home.Type.Carriers is not null)
        {
            TickCarrier(world);
            UpdateExpression();
            return;
        }
        if (Home.Workplace is not Workplace work)
        {
            TickPost(world);
            UpdateExpression();
            return;
        }

        if (Task == VillagerTask.Waiting || Task == VillagerTask.Unemployed)
            _idleTicks++;
        else
            _idleTicks = 0;

        switch (Task)
        {
            case VillagerTask.Waiting:
                if (--_retryIn <= 0)
                    Plan(world, work);
                break;
            case VillagerTask.GoingToResource:
                if (Target is null || Target.IsDepleted)
                    Plan(world, work);
                else if (FollowPath(world))
                    Task = VillagerTask.Gathering;
                break;
            case VillagerTask.Gathering:
                Gather(world, work);
                break;
            case VillagerTask.ReturningHome:
                if (FollowPath(world))
                    Deliver(world, work);
                break;
        }
        UpdateExpression();
    }

    /// <summary>
    /// Tabela do GDD, do mais forte para o mais fraco: dormindo, feliz (acabou de entregar), esforço
    /// (coletando ou levando a carga), preocupado (trabalho parado: cabana cheia, mesmo com carga na mão),
    /// sonolento (ocioso há muito tempo), distraído. Espantado, chorando e bravo ainda não têm gatilho
    /// (horda, ferimento, interrupção).
    /// </summary>
    private void UpdateExpression()
    {
        Expression = Resting ? VillagerExpression.Sleeping
            : _happyTicks > 0 ? VillagerExpression.Happy
            : Task == VillagerTask.Gathering || Task == VillagerTask.AtPost || (CarryingCount > 0 && Task != VillagerTask.Waiting)
                ? VillagerExpression.Effort
            : _hutFull ? VillagerExpression.Worried
            : _idleTicks >= SleepyAfterTicks ? VillagerExpression.Sleepy
            : VillagerExpression.Distracted;
    }

    private void Replan(SimWorld world)
    {
        if (Home?.Workplace is Workplace work)
            Plan(world, work);
        else if (Home?.Type.Carriers is not null)
            PlanHaul(world);
        else
            PlanPost(world);
    }

    /// <summary>
    /// Carregador: busca bruto num baú ou cabana dentro do raio do posto e leva até a máquina, no
    /// raio, que ainda aceita esse item (descontando o que outros carregadores já levam para ela). Sobra na mão vai para a
    /// próxima máquina que aceitar.
    /// </summary>
    private void TickCarrier(SimWorld world)
    {
        switch (Task)
        {
            case VillagerTask.Waiting:
                if (--_retryIn <= 0)
                    PlanHaul(world);
                break;
            case VillagerTask.Fetching:
                if (HaulFrom is null || world.BuildingAt(HaulFrom.Cell) != HaulFrom)
                    PlanHaul(world);
                else if (FollowPath(world))
                    PickUp(world);
                break;
            case VillagerTask.Hauling:
                if (HaulTo is null || world.BuildingAt(HaulTo.Cell) != HaulTo)
                    PlanHaul(world);
                else if (FollowPath(world))
                    DropOff(world);
                break;
        }
    }

    private void PlanHaul(SimWorld world)
    {
        _retryIn = RetryTicks;
        HaulFrom = HaulTo = null;
        HaulKind = null;
        HaulAmount = 0;
        Building post = Home!;
        float radius = post.Type.Carriers!.Radius;
        bool InRange(Building b) => Vector2.Distance(new Vector2(post.Cell.X, post.Cell.Z), new Vector2(b.Cell.X, b.Cell.Z)) <= radius;

        var machines = new List<Building>();
        var sources = new List<Building>();
        foreach (Building b in world.Buildings)
        {
            if (!InRange(b))
                continue;
            if (b.Machine is not null)
                machines.Add(b);
            else if (b.Storage is not null || b.Workplace is not null)
                sources.Add(b);
        }
        machines.Sort((a, b) => Distance(a.Cell).CompareTo(Distance(b.Cell)));

        // Já com carga: leva para a máquina mais perto que aceita.
        if (CarryingKind is string carried && CarryingCount > 0)
        {
            foreach (Building m in machines)
            {
                int need = Need(world, m, carried);
                if (need > 0 && TrySetPath(world, FreeNeighbors(world, m.Cell)))
                {
                    HaulTo = m;
                    HaulKind = carried;
                    HaulAmount = Math.Min(CarryingCount, need);
                    Task = VillagerTask.Hauling;
                    _noPath = false;
                    return;
                }
            }
            Task = VillagerTask.Waiting;
            return;
        }

        foreach (Building m in machines)
        {
            foreach (string kind in m.Machine!.Recipe.Inputs.Keys)
            {
                int need = world.IsRaw(kind) ? Need(world, m, kind) : 0;
                if (need <= 0)
                    continue;
                Building? best = null;
                foreach (Building src in sources)
                    if (Stock(src, kind) > 0 && (best is null || Distance(src.Cell) < Distance(best.Cell)))
                        best = src;
                if (best is null || !TrySetPath(world, FreeNeighbors(world, best.Cell)))
                    continue;
                HaulFrom = best;
                HaulTo = m;
                HaulKind = kind;
                HaulAmount = Math.Min(Stats.Carry, need);
                Task = VillagerTask.Fetching;
                _noPath = false;
                return;
            }
        }
        Task = VillagerTask.Waiting;
    }

    /// <summary>Quanto de <paramref name="kind"/> ainda cabe na máquina, descontando o que outros carregadores já levam.</summary>
    private int Need(SimWorld world, Building machine, string kind)
    {
        int need = machine.Machine!.Room(kind);
        foreach (Villager other in world.Villagers)
            if (other != this && other.HaulTo == machine && other.HaulKind == kind)
                need -= other.HaulAmount;
        return need;
    }

    private static int Stock(Building source, string kind) =>
        source.Storage?.Count(kind) ?? source.Workplace?.Stored.Count(kind) ?? 0;

    private void PickUp(SimWorld world)
    {
        Building src = HaulFrom!;
        Inventory? stock = src.Storage ?? src.Workplace?.Stored;
        int taken = 0;
        while (stock is not null && taken < HaulAmount && stock.TryRemoveOne(HaulKind!))
            taken++;
        if (taken == 0)
        {
            PlanHaul(world); // alguém levou antes
            return;
        }
        CarryingKind = HaulKind;
        CarryingCount = taken;
        HaulAmount = taken;
        HaulFrom = null;
        if (TrySetPath(world, FreeNeighbors(world, HaulTo!.Cell)))
            Task = VillagerTask.Hauling;
        else
            PlanHaul(world);
    }

    private void DropOff(SimWorld world)
    {
        MachineState machine = HaulTo!.Machine!;
        int given = 0;
        while (CarryingCount > 0 && machine.Accepts(CarryingKind!))
        {
            machine.Input.Add(CarryingKind!);
            CarryingCount--;
            given++;
        }
        if (CarryingCount == 0)
            CarryingKind = null;
        if (given > 0)
            _happyTicks = HappyTicks;
        Vector2 toMachine = new Vector2(HaulTo.Cell.X, HaulTo.Cell.Z) - Position;
        if (toMachine != Vector2.Zero)
            Facing = Vector2.Normalize(toMachine);
        PlanHaul(world);
    }

    /// <summary>
    /// Posto de máquina: vai até uma célula livre encostada nela (de preferência de lado, não na diagonal, e não a de um
    /// colega de posto) e fica lá. Se a célula fechar (alguém construiu em cima), escolhe outra.
    /// </summary>
    private void TickPost(SimWorld world)
    {
        switch (Task)
        {
            case VillagerTask.Waiting:
                if (--_retryIn <= 0)
                    PlanPost(world);
                break;
            case VillagerTask.GoingToPost:
                if (FollowPath(world))
                    ArriveAtPost();
                break;
            case VillagerTask.AtPost:
                if (PostCell is GridPos cell && world.BlocksVillager(cell))
                    PlanPost(world);
                break;
        }
    }

    private void PlanPost(SimWorld world)
    {
        _retryIn = RetryTicks;
        Building home = Home!;
        var taken = new HashSet<GridPos>();
        foreach (Villager? mate in home.Crew)
            if (mate is not null && mate != this && mate.PostCell is GridPos c)
                taken.Add(c);
        List<GridPos> goals = FreeNeighbors(world, home.Cell);
        goals.RemoveAll(taken.Contains);
        // Chão livre antes de cima de esteira; de lado (encostado de verdade) antes da diagonal.
        List<GridPos> sides = goals.FindAll(g => g.X == home.Cell.X || g.Z == home.Cell.Z);
        List<GridPos> clearSides = sides.FindAll(g => world.BuildingAt(g) is null);
        List<GridPos> clear = goals.FindAll(g => world.BuildingAt(g) is null);
        foreach (List<GridPos> choice in new[] { clearSides, clear, sides, goals })
        {
            if (choice.Count == 0 || !TrySetPath(world, choice))
                continue;
            PostCell = _path.Count > 0 ? LastOf(_path) : Cell;
            _noPath = false;
            Task = VillagerTask.GoingToPost;
            if (_path.Count == 0)
                ArriveAtPost();
            return;
        }
        _noPath = true;
        PostCell = null;
        Task = VillagerTask.Waiting;
    }

    private void ArriveAtPost()
    {
        Task = VillagerTask.AtPost;
        Vector2 toMachine = new Vector2(Home!.Cell.X, Home.Cell.Z) - Position;
        if (toMachine != Vector2.Zero)
            Facing = Vector2.Normalize(toMachine);
    }

    private static GridPos LastOf(Queue<GridPos> queue)
    {
        GridPos last = default;
        foreach (GridPos g in queue)
            last = g;
        return last;
    }

    /// <summary>Decide o próximo passo: entregar a carga, ou buscar o recurso mais perto dentro do raio.</summary>
    private void Plan(SimWorld world, Workplace work)
    {
        _retryIn = RetryTicks;
        if (CarryingCount > 0)
        {
            GoHome(world);
            return;
        }
        _hutFull = work.Free <= 0;
        if (_hutFull)
        {
            Task = VillagerTask.Waiting;
            return;
        }

        // Do mais perto (em linha reta) ao mais longe, o primeiro que tiver caminho.
        var candidates = new List<ResourceNode>();
        var homeCenter = new Vector2(Home!.Cell.X, Home.Cell.Z);
        foreach (ResourceNode node in world.Resources)
        {
            if (!node.IsDepleted && node.Kind == work.Job.Resource &&
                Vector2.Distance(homeCenter, new Vector2(node.Cell.X, node.Cell.Z)) <= work.Job.Radius)
                candidates.Add(node);
        }
        candidates.Sort((a, b) => Distance(a.Cell).CompareTo(Distance(b.Cell)));
        _noResource = candidates.Count == 0;

        foreach (ResourceNode node in candidates)
        {
            if (TrySetPath(world, FreeNeighbors(world, node.Cell)))
            {
                Target = node;
                Task = VillagerTask.GoingToResource;
                _noPath = false;
                return;
            }
        }
        _noPath = candidates.Count > 0;
        Target = null;
        Task = VillagerTask.Waiting;
    }

    private void Gather(SimWorld world, Workplace work)
    {
        ResourceNode? node = Target;
        if (node is null || node.IsDepleted)
        {
            Plan(world, work);
            return;
        }
        if (!Touching(world, node))
            return;

        Vector2 toNode = new Vector2(node.Cell.X, node.Cell.Z) - Position;
        if (toNode != Vector2.Zero)
            Facing = Vector2.Normalize(toNode);

        if (++_gatherTicks < GatherTicksFor(node))
            return;
        _gatherTicks = 0;
        if (node.TakeOne())
        {
            CarryingKind = node.Kind;
            CarryingCount++;
        }
        if (CarryingCount >= Stats.Carry || node.IsDepleted)
            GoHome(world);
    }

    /// <summary>
    /// Recurso com forma (tronco, base da pedra): antes de coletar, chega da célula vizinha até encostar na borda real
    /// dela. Devolve true quando já está encostado; sem forma, sempre true (coleta da célula vizinha, como antes).
    /// </summary>
    private bool Touching(SimWorld world, ResourceNode node)
    {
        if (node.Shape is not ResourceShape shape)
            return true;
        var center = new Vector2(node.Cell.X, node.Cell.Z);
        Vector2 toTrunk = center - Position;
        float gap = shape.SignedDistance(Position) - Stats.Radius;
        if (gap <= 0.02f || toTrunk.LengthSquared() < 1e-8f)
            return true;
        float step = MathF.Min(gap, Speed / SimClock.TicksPerSecond);
        Facing = Vector2.Normalize(toTrunk);
        Position = world.PushOutOfTrunks(Position + Facing * step, Stats.Radius);
        return false;
    }

    private void GoHome(SimWorld world)
    {
        _noPath = !TrySetPath(world, FreeNeighbors(world, Home!.Cell));
        Task = _noPath ? VillagerTask.Waiting : VillagerTask.ReturningHome;
    }

    private void Deliver(SimWorld world, Workplace work)
    {
        if (CarryingKind is string kind && CarryingCount > 0)
        {
            int amount = Math.Min(CarryingCount, work.Free);
            work.Stored.Add(kind, amount);
            CarryingCount -= amount;
            if (CarryingCount == 0)
                CarryingKind = null;
            if (amount > 0)
                _happyTicks = HappyTicks;
        }
        _hutFull = CarryingCount > 0; // sobrou carga: a cabana está cheia
        // Se a cabana encheu, espera com o resto da carga.
        Task = VillagerTask.Waiting;
        _retryIn = CarryingCount > 0 ? RetryTicks : 0;
    }

    /// <summary>
    /// Anda pelo caminho; true quando chegou. Se a próxima célula virou sólida, replaneja. Célula de árvore no caminho
    /// conta como atingida ao encostar no tronco; dali, rumo à próxima, o aldeão escorrega em volta do tronco.
    /// </summary>
    private bool FollowPath(SimWorld world)
    {
        float budget = Speed / SimClock.TicksPerSecond;
        while (budget > 0f && _path.Count > 0)
        {
            GridPos next = _path.Peek();
            if (world.BlocksVillager(next))
            {
                _path.Clear();
                Replan(world);
                return false;
            }
            var target = new Vector2(next.X, next.Z);
            Vector2 delta = target - Position;
            float distance = delta.Length();
            if (world.ShapeAt(next) is ResourceShape shape)
            {
                // Célula de recurso: conta como atingida ao encostar na forma; dali escorrega rumo à próxima.
                if (shape.SignedDistance(Position) <= Stats.Radius + 0.05f || distance < 1e-5f)
                {
                    _path.Dequeue();
                    continue;
                }
                float move = MathF.Min(budget, distance);
                Vector2 toward = delta / distance * move;
                Facing = delta / distance;
                Position = SlideAroundTrunks(world, toward);
                return false;
            }
            if (distance > budget)
            {
                Vector2 step = delta / distance * budget;
                Facing = step / budget;
                Position = SlideAroundTrunks(world, step);
                return false;
            }
            Position = target;
            budget -= distance;
            _path.Dequeue();
        }
        return _path.Count == 0;
    }

    /// <summary>
    /// Um passo que bateria num tronco vira o passo ao longo da tangente (escorrega em volta dele); de frente, sem
    /// tangente, escolhe um lado pelo id, sempre o mesmo. Depois empurra para fora de qualquer tronco.
    /// </summary>
    private Vector2 SlideAroundTrunks(SimWorld world, Vector2 step)
    {
        Vector2 next = Position + step;
        Vector2 pushed = world.PushOutOfTrunks(next, Stats.Radius);
        if (pushed == next)
            return next;
        Vector2 normal = Vector2.Normalize(pushed - next);
        float into = Vector2.Dot(step, normal);
        if (into < 0f)
        {
            Vector2 tangent = step - normal * into;
            float length = step.Length();
            if (tangent.Length() < 0.3f * length)
            {
                // De frente: vai para o lado com mais folga das células cheias (pedra, construção); empate, pelo id.
                var side = new Vector2(-normal.Y, normal.X) * length;
                float left = Clearance(world, Position + side), right = Clearance(world, Position - side);
                float sign = MathF.Abs(left - right) > 0.01f ? (left > right ? 1f : -1f) : (Id % 2 == 0 ? 1f : -1f);
                tangent = side * sign;
            }
            next = Position + tangent;
        }
        return world.PushOutOfTrunks(next, Stats.Radius);
    }

    /// <summary>Distância de uma posição até a célula cheia mais perto em volta (até 1,5; mais que isso não importa).</summary>
    private static float Clearance(SimWorld world, Vector2 position)
    {
        float best = 1.5f;
        int cx = (int)MathF.Round(position.X), cz = (int)MathF.Round(position.Y);
        for (int dx = -1; dx <= 1; dx++)
        for (int dz = -1; dz <= 1; dz++)
        {
            var cell = new GridPos(cx + dx, cz + dz);
            if (!world.BlocksVillager(cell))
                continue;
            float ox = MathF.Max(MathF.Abs(position.X - cell.X) - 0.5f, 0f);
            float oz = MathF.Max(MathF.Abs(position.Y - cell.Z) - 0.5f, 0f);
            best = MathF.Min(best, MathF.Sqrt(ox * ox + oz * oz));
        }
        return best;
    }

    private bool TrySetPath(SimWorld world, List<GridPos> goals)
    {
        List<GridPos>? path = GridPath.Find(world.BlocksVillager, Cell, goals,
            cell => world.ShapeAt(cell) is null ? 0f : Stats.ResourceCellCost);
        if (path is null)
            return false;
        _path.Clear();
        foreach (GridPos cell in path)
            _path.Enqueue(cell);
        return true;
    }

    /// <summary>Células livres encostadas (8 vizinhas) numa célula: de onde dá para coletar ou entregar.</summary>
    private static List<GridPos> FreeNeighbors(SimWorld world, GridPos cell)
    {
        var list = new List<GridPos>();
        for (int dx = -1; dx <= 1; dx++)
        for (int dz = -1; dz <= 1; dz++)
        {
            var n = new GridPos(cell.X + dx, cell.Z + dz);
            if ((dx != 0 || dz != 0) && !world.IsSolid(n))
                list.Add(n);
        }
        return list;
    }

    private float Distance(GridPos cell) => Vector2.Distance(Position, new Vector2(cell.X, cell.Z));

    private int GatherTicksFor(ResourceNode node) =>
        Math.Max(1, (int)MathF.Round(node.Type.GatherTicks * Stats.GatherMultiplier));
}
