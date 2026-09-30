using System;
using System.Collections.Generic;
using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>O que o aldeão está fazendo agora (para a animação e o estado).</summary>
public enum VillagerTask
{
    /// <summary>Parado: sem ladainha, entre dois comandos, ou esperando depois de travar.</summary>
    Waiting,
    /// <summary>Andando até o alvo do comando.</summary>
    GoingToResource,
    /// <summary>Colhendo, arrancando ou cavando.</summary>
    Gathering,
    /// <summary>Encostado na máquina, no posto (comando "operar"): conta para a equipe dela.</summary>
    AtPost,
}

/// <summary>
/// Aldeão (GDD, seção 6; docs/ladainhas.md). NÃO FAZ NADA SOZINHO: sem ladainha fica parado; com ela, repete os comandos
/// (caminho A*). Aldeões não colidem entre si nem com o Castelão. A célula de árvore não bloqueia o caminho (só o tronco):
/// eles passam sob a copa, deslizando em volta do tronco, e colhem encostados nele.
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

    /// <summary>
    /// Nasceu vazio no Cristal-mãe e espera uma ladainha (docs/ladainhas.md): nenhuma construção o chama para posto.
    /// </summary>
    public bool Blank { get; internal set; }

    /// <summary>Força (docs/ladainhas.md): quantos pesados leva por viagem, 1 por ponto. Nasce com 1.</summary>
    public int Strength { get; internal set; } = 1;

    /// <summary>Agilidade: +10% de velocidade por ponto acima de 1 (data/villagers.json, agilityBonus). Nasce com 1.</summary>
    public int Agility { get; internal set; } = 1;

    /// <summary>Inteligência: tamanho da ladainha e quais comandos entende. Nasce com 1.</summary>
    public int Intelligence { get; internal set; } = 1;

    /// <summary>A ladainha que ele repete, ou null (parado: o aldeão não faz nada sozinho).</summary>
    public Litany? Litany { get; private set; }

    /// <summary>Índice do comando atual da ladainha.</summary>
    public int CommandIndex { get; private set; }

    /// <summary>O comando atual, ou null sem ladainha.</summary>
    public LitanyCommand? CurrentCommand => Litany?.Commands[CommandIndex];

    /// <summary>Por que o comando atual travou, ou null se está andando (docs/ladainhas.md: nunca travar calado).</summary>
    public LitanyStuck? Stuck { get; private set; }

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
    /// <summary>A máquina em cujo posto ele está (só enquanto o comando "operar" dura), ou null.</summary>
    public Building? Home { get; private set; }
    public VillagerTask Task { get; private set; } = VillagerTask.Waiting;

    /// <summary>Estado para o ícone: descansando, sem ladainha, travado (o motivo em <see cref="Stuck"/>) ou rezando.</summary>
    public VillagerStatus Status =>
        Resting ? VillagerStatus.Resting
        : Litany is null ? VillagerStatus.NoLitany
        : Stuck is not null ? VillagerStatus.Stuck
        : VillagerStatus.Chanting;
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

    /// <summary>O baú onde vai soltar a carga ao começar uma ladainha, ou null.</summary>
    private Building? _dropAt;

    private readonly Queue<GridPos> _path = new();
    // Ladainha: estado do comando atual (começou? ticks nele) e a espera depois de travar (1 s dobrando até 8 s).
    private bool _commandStarted;
    private int _commandTicks;
    private int _stuckWait;
    private int _stuckCount;
    private bool _dropFirst;

    /// <summary>Quantos itens ele reservou no lugar de onde vai pegar (outros aldeões não contam com eles).</summary>
    internal int ReservedAmount { get; private set; }

    /// <summary>A célula de margem que ele está cavando (reservada: outro aldeão não escolhe a mesma).</summary>
    public GridPos? DigCell { get; private set; }
    private int _gatherTicks;
    private int _idleTicks;
    private int _happyTicks;

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

    /// <summary>Põe itens na mão dele (testes).</summary>
    internal void GiveForTests(string kind, int count)
    {
        CarryingKind = kind;
        CarryingCount = count;
    }

    /// <summary>Esvazia a carga no inventário dado.</summary>
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
        Speed = Stats.FinalSpeed(SpeedTier, world.FloorBonusAt(Cell), Penalized) * (1f + Stats.AgilityBonus * (Agility - 1));
        if (_happyTicks > 0)
            _happyTicks--;
        if (Litany is not null)
        {
            _idleTicks = 0;
            TickLitany(world);
            UpdateExpression();
            return;
        }
        // Sem ladainha: parado (o aldeão não faz nada sozinho).
        _idleTicks++;
        UpdateExpression();
    }

    /// <summary>
    /// Tabela do GDD, do mais forte para o mais fraco: dormindo, feliz (acabou de entregar), esforço
    /// (colhendo, no posto ou levando carga), preocupado (a ladainha travou), sonolento (ocioso há muito tempo),
    /// distraído. Espantado, chorando e bravo ainda não têm gatilho
    /// (horda, ferimento, interrupção).
    /// </summary>
    private void UpdateExpression()
    {
        Expression = Resting ? VillagerExpression.Sleeping
            : _happyTicks > 0 ? VillagerExpression.Happy
            : Task == VillagerTask.Gathering || Task == VillagerTask.AtPost || (CarryingCount > 0 && Task != VillagerTask.Waiting)
                ? VillagerExpression.Effort
            : Stuck is not null ? VillagerExpression.Worried
            : _idleTicks >= SleepyAfterTicks ? VillagerExpression.Sleepy
            : VillagerExpression.Distracted;
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
                _commandStarted = false; // a ladainha recalcula o caminho no próximo tick
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

    // ---- Ladainhas (docs/ladainhas.md) ------------------------------------------------------------------------

    /// <summary>Se ele aceitaria essa ladainha, e por que não: tamanho e comandos cabem na Inteligência dele?</summary>
    public LitanyFit CanLearn(Litany litany) =>
        litany.Commands.Count == 0 ? LitanyFit.Empty
        : litany.RequiredIntelligence > Intelligence ? LitanyFit.TooHard
        : litany.Commands.Count > Stats.MaxCommands(Intelligence) ? LitanyFit.TooLong
        : LitanyFit.Ok;

    /// <summary>
    /// Recebe uma ladainha (ou null: para e fica parado). Recusa o que não cabe na Inteligência. Começa do primeiro
    /// comando; sai do posto em que estivesse (quem manda agora é a ladainha).
    /// </summary>
    internal LitanyFit Learn(SimWorld world, Litany? litany)
    {
        if (litany is not null && CanLearn(litany) is var fit && fit != LitanyFit.Ok)
            return fit;
        LeaveHome(world);
        Litany = litany;
        Blank = false;
        CommandIndex = 0;
        ResetCommand();
        Stuck = null;
        _stuckCount = 0;
        _stuckWait = 0;
        _dropFirst = litany is not null && CarryingCount > 0;
        Task = VillagerTask.Waiting;
        return LitanyFit.Ok;
    }

    /// <summary>Solta o posto ou a cabana em que estava (ladainha nova, ou fim do "operar").</summary>
    private void LeaveHome(SimWorld world)
    {
        if (Home is Building home)
        {
            for (int i = 0; i < home.Crew.Length; i++)
                if (home.Crew[i] == this)
                    home.Crew[i] = null;
        }
        Home = null;
        PostCell = null;
        _dropAt = null;
        Target = null;
        _path.Clear();
    }

    private void ResetCommand()
    {
        _commandStarted = false;
        _commandTicks = 0;
        _gatherTicks = 0;
        ReservedAmount = 0;
        Target = null;
        DigCell = null;
        _path.Clear();
        if (Task != VillagerTask.AtPost)
            Task = VillagerTask.Waiting;
    }

    /// <summary>Um comando por vez; terminou, passa ao próximo (depois do último, volta ao primeiro).</summary>
    private void TickLitany(SimWorld world)
    {
        if (_stuckWait > 0)
        {
            _stuckWait--;
            return;
        }
        Stuck = null; // tenta de novo: se falhar outra vez, o motivo volta no mesmo tick
        if (_dropFirst)
        {
            DropFirst(world);
            return;
        }
        LitanyCommand command = Litany!.Commands[CommandIndex];
        bool done = command.Verb switch
        {
            LitanyVerb.Wait => ++_commandTicks >= command.Ticks,
            LitanyVerb.GoTo => DoGoTo(world, command.Target!),
            _ => DoAction(world, command),
        };
        if (!done)
            return;
        Stuck = null;
        _stuckCount = 0;
        CommandIndex = (CommandIndex + 1) % Litany.Commands.Count;
        ResetCommand();
    }

    private bool DoAction(SimWorld world, LitanyCommand command) => command.Verb switch
    {
        LitanyVerb.Take => DoTake(world, command.Item!, command.Target!.Cell),
        LitanyVerb.Put => DoPut(world, command.Item!, command.Target!.Cell),
        LitanyVerb.Gather => DoGather(world, command.Target!),
        LitanyVerb.Operate => DoOperate(world, command.Target!.Cell),
        _ => true,
    };

    /// <summary>
    /// Estado inicial previsível (docs/ladainhas.md): ao começar uma ladainha, solta o que carrega no baú mais perto dentro
    /// do raio; sem baú, começa carregando.
    /// </summary>
    private void DropFirst(SimWorld world)
    {
        if (!_commandStarted)
        {
            Building? chest = null;
            foreach (Building b in world.Buildings)
                if (b.Storage is not null && Distance(b.Cell) <= Stats.LitanyRadius && (chest is null || Distance(b.Cell) < Distance(chest.Cell)))
                    chest = b;
            if (chest is null || CarryingCount == 0 || !TrySetPath(world, FreeNeighbors(world, chest.Cell)))
            {
                _dropFirst = false;
                ResetCommand();
                return;
            }
            _dropAt = chest;
            _commandStarted = true;
        }
        if (!FollowPath(world))
            return;
        if (_dropAt is { Storage: Inventory storage } && world.BuildingAt(_dropAt.Cell) == _dropAt && CarryingKind is string kind)
            storage.Add(kind, CarryingCount);
        CarryingKind = null;
        CarryingCount = 0;
        _dropAt = null;
        _dropFirst = false;
        ResetCommand();
    }

    /// <summary>O estoque de onde se pega: baú, saída de máquina ou cabana.</summary>
    private static Inventory? StockOf(Building b) => b.Storage ?? b.Machine?.Output ?? b.Workplace?.Stored;

    /// <summary>Pegar [item] de [lugar]: vai até ele e pega o quanto couber (reservando, para outro não contar com isso).</summary>
    private bool DoTake(SimWorld world, string item, GridPos cell)
    {
        if (world.BuildingAt(cell) is not Building place || StockOf(place) is not Inventory stock)
        {
            Fail(LitanyStuck.NoPlace);
            return false;
        }
        int capacity = CarryFor(world, item);
        if (capacity <= 0)
        {
            Fail(LitanyStuck.TooHeavy);
            return false;
        }
        if (CarryingKind is string other && other != item && CarryingCount > 0)
        {
            Fail(LitanyStuck.HandsFull);
            return false;
        }
        int room = capacity - CarryingCount;
        if (room <= 0)
            return true; // já está com a carga cheia desse item
        if (!_commandStarted)
        {
            int free = stock.Count(item) - ReservedBy(world, place, item);
            if (free <= 0)
            {
                Fail(LitanyStuck.SourceEmpty);
                return false;
            }
            ReservedAmount = Math.Min(room, free);
        }
        if (!WalkTo(world, FreeNeighbors(world, place.Cell)))
            return false;
        int taken = 0;
        while (taken < room && stock.TryRemoveOne(item))
            taken++;
        ReservedAmount = 0;
        if (taken == 0)
        {
            Fail(LitanyStuck.SourceEmpty);
            return false;
        }
        CarryingKind = item;
        CarryingCount += taken;
        Face(place.Cell);
        return true;
    }

    /// <summary>Quanto desse item no lugar já está reservado por outros aldeões a caminho.</summary>
    private int ReservedBy(SimWorld world, Building place, string item)
    {
        int reserved = 0;
        foreach (Villager other in world.Villagers)
            if (other != this && other.ReservedAmount > 0 && other.CurrentCommand is { Verb: LitanyVerb.Take } c &&
                c.Item == item && c.Target!.Cell == place.Cell)
                reserved += other.ReservedAmount;
        return reserved;
    }

    /// <summary>Pôr [item] em [lugar]: baú (sempre cabe), entrada de máquina (até 2 ciclos) ou cabana.</summary>
    private bool DoPut(SimWorld world, string item, GridPos cell)
    {
        if (world.BuildingAt(cell) is not Building place)
        {
            Fail(LitanyStuck.NoPlace);
            return false;
        }
        if (CarryingKind != item || CarryingCount <= 0)
        {
            Fail(LitanyStuck.HandsEmpty);
            return false;
        }
        int Room() => place.Storage is not null ? int.MaxValue
            : place.Machine is MachineState m ? m.Room(item)
            : place.Workplace is Workplace w ? w.Free
            : -1;
        int room = Room();
        if (room < 0 || (place.Machine is MachineState mm && !mm.Recipe.Inputs.ContainsKey(item)))
        {
            Fail(LitanyStuck.NotAccepted);
            return false;
        }
        if (room == 0)
        {
            Fail(LitanyStuck.TargetFull);
            return false;
        }
        if (!WalkTo(world, FreeNeighbors(world, place.Cell)))
            return false;
        int amount = Math.Min(CarryingCount, Room());
        if (amount <= 0)
        {
            Fail(LitanyStuck.TargetFull);
            return false;
        }
        Inventory target = place.Storage ?? place.Machine?.Input ?? place.Workplace!.Stored;
        target.Add(item, amount);
        CarryingCount -= amount;
        if (CarryingCount == 0)
            CarryingKind = null;
        _happyTicks = HappyTicks;
        Face(place.Cell);
        return true;
    }

    /// <summary>
    /// Colher, arrancar ou cavar o recurso mais perto dele dentro do raio em volta do ponto gravado (reservando o alvo),
    /// até encher a carga ou o recurso acabar. "Argila" cava a margem, que não esgota.
    /// </summary>
    private bool DoGather(SimWorld world, LitanyTarget target)
    {
        string kind = target.Resource!;
        int capacity = CarryFor(world, kind);
        if (capacity <= 0)
        {
            Fail(LitanyStuck.TooHeavy);
            return false;
        }
        if (CarryingKind is string other && other != kind && CarryingCount > 0)
        {
            Fail(LitanyStuck.HandsFull);
            return false;
        }
        if (CarryingCount >= capacity)
            return true;
        bool digging = world.Data.Castellan.Dig is DigType dig && dig.Item == kind;
        if (!_commandStarted)
        {
            if (AreaOf(world, target) is not (GridPos, float) area)
            {
                Fail(LitanyStuck.NoPlace);
                return false;
            }
            if (digging ? !PickBank(world, target.Resource!, area.Center, area.Radius) : !PickResource(world, target.Resource!, area.Center, area.Radius))
            {
                Fail(LitanyStuck.NoResource);
                return false;
            }
        }
        if (Task != VillagerTask.Gathering)
        {
            GridPos cell = digging ? DigCell!.Value : Target!.Cell;
            List<GridPos> goals = FreeNeighbors(world, cell);
            if (digging && !world.IsSolid(cell))
                goals.Add(cell);
            if (!WalkTo(world, goals))
                return false;
            _commandStarted = true; // chegou: continua com o mesmo alvo
            Task = VillagerTask.Gathering;
        }
        if (!digging)
        {
            if (Target is null || Target.IsDepleted)
                return CarryingCount > 0 || FailAndFalse(LitanyStuck.NoResource);
            if (!Touching(world, Target))
                return false;
            Face(Target.Cell);
            if (++_gatherTicks < GatherTicksFor(Target))
                return false;
            _gatherTicks = 0;
            if (Target.TakeOne())
            {
                CarryingKind = kind;
                CarryingCount++;
            }
            return CarryingCount >= capacity || Target.IsDepleted;
        }
        Face(DigCell!.Value);
        int digTicks = Math.Max(1, (int)MathF.Round(world.Data.Castellan.Dig!.Ticks * Stats.GatherMultiplier));
        if (++_gatherTicks < digTicks)
            return false;
        _gatherTicks = 0;
        CarryingKind = kind;
        CarryingCount++;
        return CarryingCount >= capacity;
    }

    private bool FailAndFalse(LitanyStuck reason)
    {
        Fail(reason);
        return false;
    }

    /// <summary>
    /// A área de busca do colher: em volta do ponto gravado com o raio dele, ou a área da cabana/Posto de Carregadores
    /// citado (o raio dela; sem raio próprio, o padrão). null se o lugar citado sumiu.
    /// </summary>
    private (GridPos Center, float Radius)? AreaOf(SimWorld world, LitanyTarget target)
    {
        if (!target.Anchored)
            return (target.Cell, target.Radius);
        if (world.BuildingAt(target.Cell) is not Building place)
            return null;
        return (target.Cell, place.Type.Job?.Radius ?? place.Type.Carriers?.Radius ?? Stats.LitanyRadius);
    }

    /// <summary>O recurso livre mais perto dele na área (sem construção em cima, sem reserva).</summary>
    private bool PickResource(SimWorld world, string kind, GridPos centerCell, float radius)
    {
        var center = new Vector2(centerCell.X, centerCell.Z);
        ResourceNode? best = null;
        foreach (ResourceNode node in world.Resources)
        {
            if (node.IsDepleted || node.Kind != kind || world.BuildingAt(node.Cell) is not null ||
                Vector2.Distance(center, new Vector2(node.Cell.X, node.Cell.Z)) > radius)
                continue;
            bool reserved = false;
            foreach (Villager other in world.Villagers)
                if (other != this && other.Target == node)
                    reserved = true;
            if (!reserved && (best is null || Distance(node.Cell) < Distance(best.Cell)))
                best = node;
        }
        Target = best;
        return best is not null;
    }

    /// <summary>A célula de margem livre mais perto dele na área (sem construção, sem reserva).</summary>
    private bool PickBank(SimWorld world, string kind, GridPos centerCell, float radius)
    {
        int r = (int)MathF.Ceiling(radius);
        var center = new Vector2(centerCell.X, centerCell.Z);
        GridPos? best = null;
        for (int dx = -r; dx <= r; dx++)
        for (int dz = -r; dz <= r; dz++)
        {
            var cell = new GridPos(centerCell.X + dx, centerCell.Z + dz);
            if (!world.IsBank(cell) || world.BuildingAt(cell) is not null || Vector2.Distance(center, new Vector2(cell.X, cell.Z)) > radius)
                continue;
            bool reserved = false;
            foreach (Villager other in world.Villagers)
                if (other != this && other.DigCell == cell)
                    reserved = true;
            if (!reserved && (best is null || Distance(cell) < Distance(best.Value)))
                best = cell;
        }
        DigCell = best;
        return best is not null;
    }

    /// <summary>
    /// Operar [máquina] até ela ficar sem insumo ou com a saída cheia: ocupa um posto vago (como a protagonista), vai
    /// até encostar e fica; depois solta o posto e segue a ladainha.
    /// </summary>
    private bool DoOperate(SimWorld world, GridPos cell)
    {
        if (world.BuildingAt(cell) is not Building machine)
        {
            LeaveHome(world);
            Fail(LitanyStuck.NoPlace);
            return false;
        }
        if (machine.Type.Posts is null || machine.Machine is null)
        {
            Fail(LitanyStuck.NoPost);
            return false;
        }
        if (Home != machine)
        {
            int slot = -1;
            for (int i = 0; i < machine.Crew.Length && slot < 0; i++)
                if (machine.Crew[i] is null && machine.CastellanSlot != i)
                    slot = i;
            if (slot < 0)
            {
                Fail(LitanyStuck.PostTaken);
                return false;
            }
            machine.Crew[slot] = this;
            Home = machine;
        }
        if (Task != VillagerTask.AtPost)
        {
            var taken = new HashSet<GridPos>();
            foreach (Villager? mate in machine.Crew)
                if (mate is not null && mate != this && mate.Task == VillagerTask.AtPost)
                    taken.Add(mate.Cell);
            List<GridPos> goals = FreeNeighbors(world, machine.Cell);
            goals.RemoveAll(taken.Contains);
            List<GridPos> sides = goals.FindAll(g => g.X == machine.Cell.X || g.Z == machine.Cell.Z);
            if (!WalkTo(world, sides.Count > 0 ? sides : goals))
            {
                if (Stuck is not null)
                    LeaveHome(world);
                return false;
            }
            Task = VillagerTask.AtPost;
            PostCell = Cell;
            Face(machine.Cell);
            _commandTicks = 0;
            return false;
        }
        // Encostado: fica enquanto a máquina trabalha ou pode começar (sem mana, espera).
        MachineState m = machine.Machine;
        if (++_commandTicks < 2 || m.IsWorking || m.CanStart)
            return false;
        LeaveHome(world);
        Task = VillagerTask.Waiting;
        return true;
    }

    private void Face(GridPos cell)
    {
        Vector2 to = new Vector2(cell.X, cell.Z) - Position;
        if (to.LengthSquared() > 1e-6f)
            Facing = Vector2.Normalize(to);
    }

    /// <summary>Travou: guarda o motivo e espera 1 s, dobrando a cada vez até 8 s, antes de tentar de novo.</summary>
    private void Fail(LitanyStuck reason)
    {
        Stuck = reason;
        _stuckWait = SimClock.TicksPerSecond << Math.Min(_stuckCount, 3);
        _stuckCount++;
        ResetCommand();
        Task = VillagerTask.Waiting;
    }

    /// <summary>Anda até ficar encostado nos alvos dados; true quando chegou.</summary>
    private bool WalkTo(SimWorld world, List<GridPos> goals)
    {
        if (!_commandStarted)
        {
            if (goals.Contains(Cell))
            {
                _path.Clear();
                return true;
            }
            if (goals.Count == 0 || !TrySetPath(world, goals))
            {
                Fail(LitanyStuck.NoPath);
                return false;
            }
            _commandStarted = true;
            Task = VillagerTask.GoingToResource;
        }
        if (!FollowPath(world))
            return false;
        _commandStarted = false;
        return true;
    }

    /// <summary>Ir até uma construção (encostado nela) ou até uma célula do chão.</summary>
    private bool DoGoTo(SimWorld world, LitanyTarget target)
    {
        List<GridPos> goals;
        if (target.Kind == LitanyTargetKind.Building)
        {
            if (world.BuildingAt(target.Cell) is null)
            {
                Fail(LitanyStuck.NoPlace);
                return false;
            }
            goals = FreeNeighbors(world, target.Cell);
        }
        else
            goals = world.IsSolid(target.Cell) ? FreeNeighbors(world, target.Cell) : new List<GridPos> { target.Cell };
        return WalkTo(world, goals);
    }

    /// <summary>Quantos desse item cabem numa viagem: pesado, 1 por ponto de Força; leve, 10 (docs/ladainhas.md).</summary>
    public int CarryFor(SimWorld world, string kind) =>
        world.Data.Item(kind).IsHeavy ? Stats.CarryHeavy * Strength : Stats.CarryLight;

    private float Distance(GridPos cell) => Vector2.Distance(Position, new Vector2(cell.X, cell.Z));

    private int GatherTicksFor(ResourceNode node) =>
        Math.Max(1, (int)MathF.Round(node.Type.GatherTicks * Stats.GatherMultiplier));
}
