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
}

/// <summary>
/// Aldeão trabalhador (GDD, seção 6). Com uma cabana, repete sozinho: acha o recurso do ofício mais
/// perto dentro do raio, anda até encostar (caminho A*), coleta até encher a carga e volta para entregar.
/// Aldeões não colidem entre si nem com o Castelão.
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
        if (Home?.Workplace is not Workplace work)
        {
            _idleTicks++;
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
            : Task == VillagerTask.Gathering || (CarryingCount > 0 && Task != VillagerTask.Waiting) ? VillagerExpression.Effort
            : _hutFull ? VillagerExpression.Worried
            : _idleTicks >= SleepyAfterTicks ? VillagerExpression.Sleepy
            : VillagerExpression.Distracted;
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

    /// <summary>Anda pelo caminho; true quando chegou. Se a próxima célula virou sólida, replaneja.</summary>
    private bool FollowPath(SimWorld world)
    {
        float budget = Speed / SimClock.TicksPerSecond;
        while (budget > 0f && _path.Count > 0)
        {
            GridPos next = _path.Peek();
            if (world.IsSolid(next))
            {
                _path.Clear();
                Plan(world, Home!.Workplace!);
                return false;
            }
            var target = new Vector2(next.X, next.Z);
            Vector2 delta = target - Position;
            float distance = delta.Length();
            if (distance > budget)
            {
                Position += delta / distance * budget;
                Facing = Vector2.Normalize(delta);
                return false;
            }
            Position = target;
            budget -= distance;
            _path.Dequeue();
        }
        return _path.Count == 0;
    }

    private bool TrySetPath(SimWorld world, List<GridPos> goals)
    {
        List<GridPos>? path = GridPath.Find(world.IsSolid, Cell, goals);
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
