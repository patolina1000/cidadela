using System;
using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>
/// O personagem principal (GDD, seção 20). Anda na direção pedida pelo último
/// <see cref="MoveCommand"/>, sem atravessar recursos e máquinas, e coleta à mão
/// o recurso pedido por <see cref="GatherCommand"/> enquanto estiver parado e encostado nele.
/// </summary>
public sealed class Castellan
{
    public int Id { get; }
    public CastellanStats Stats { get; private set; }
    public Inventory Inventory { get; } = new();

    /// <summary>Posição contínua no plano da grade (X, Z), em células; (x, z) = centro da célula x, z.</summary>
    public Vector2 Position { get; private set; }

    /// <summary>Posição no tick anterior, para a cena interpolar.</summary>
    public Vector2 PreviousPosition { get; private set; }

    /// <summary>Direção para onde está virado (unitária). Muda ao andar e ao coletar.</summary>
    public Vector2 Facing { get; private set; } = new(0f, 1f);

    /// <summary>Recurso sendo coletado, ou null.</summary>
    public ResourceNode? GatherTarget { get; private set; }

    /// <summary>Progresso do item atual, de 0 a 1.</summary>
    public float GatherProgress => GatherTarget is null ? 0f : (float)_gatherTicks / GatherTarget.Type.GatherTicks;

    /// <summary>A máquina em cujo posto ela está, ou null (docs/linha_energia.md: encostar e apertar E).</summary>
    public Building? Post { get; private set; }

    /// <summary>Quantas receitas à mão ainda estão na fila (a que está em andamento não conta).</summary>
    public int HandQueue => _handQueue.Count;

    /// <summary>A receita à mão em andamento (as entradas já saíram do inventário), ou null.</summary>
    public HandRecipe? HandCurrent { get; private set; }

    /// <summary>Se está fazendo algo à mão agora.</summary>
    public bool HandBusy => HandCurrent is not null;

    /// <summary>A próxima (ou a atual) receita à mão espera ela chegar perto da água (moldar a casca).</summary>
    public bool HandNeedsWater { get; private set; }

    /// <summary>Progresso da receita à mão em andamento, de 0 a 1.</summary>
    public float HandProgress => HandCurrent is HandRecipe r ? (float)_handTicks / r.Recipe.Ticks : 0f;

    /// <summary>Célula de margem que está cavando (argila), ou null.</summary>
    public GridPos? DigCell { get; private set; }

    /// <summary>Progresso da coleta ou da escavação atual, de 0 a 1.</summary>
    public float WorkProgress => DigCell is not null && Stats.Dig is DigType dig ? (float)_digTicks / dig.Ticks : GatherProgress;

    private readonly System.Collections.Generic.Queue<HandRecipe> _handQueue = new();
    private int _digTicks;

    private Vector2 _moveDirection;
    private int _gatherTicks;
    private int _handTicks;

    public Castellan(int id, Vector2 position, CastellanStats stats)
    {
        Id = id;
        Position = position;
        PreviousPosition = position;
        Stats = stats;
    }

    /// <summary>Troca só a velocidade (depuração: <see cref="SetCastellanSpeedCommand"/>).</summary>
    public void SetSpeed(float cellsPerSecond) => Stats = Stats with { CellsPerSecond = cellsPerSecond };

    /// <summary>Se a célula está dentro do alcance de construir (distância entre centros).</summary>
    public bool CanReach(GridPos cell) =>
        Vector2.Distance(Position, new Vector2(cell.X, cell.Z)) <= Stats.Reach;

    /// <summary>
    /// Se está perto o bastante para coletar a célula: do centro do corpo até a borda da célula; se o recurso só bloqueia
    /// uma forma (<paramref name="shape"/>: tronco, base da pedra), até a borda real dela. Encostado de lado ou na
    /// diagonal conta; uma célula de folga já não.
    /// </summary>
    public bool CanGather(GridPos cell, ResourceShape? shape = null)
    {
        Vector2 center = Position + new Vector2(0.5f, 0.5f);
        if (shape is not null)
            return shape.SignedDistance(Position) <= Stats.GatherSurfaceReach;
        var nearest = new Vector2(Math.Clamp(center.X, cell.X, cell.X + 1), Math.Clamp(center.Y, cell.Z, cell.Z + 1));
        return Vector2.Distance(center, nearest) <= Stats.GatherReach;
    }

    /// <summary>Põe o corpo numa posição (testes; o jogo só move pelo <see cref="MoveCommand"/>).</summary>
    internal void PlaceAt(Vector2 position)
    {
        Position = position;
        PreviousPosition = position;
    }

    internal void SetMoveDirection(Vector2 direction)
    {
        // Diagonal não pode ser mais rápida; entrada analógica menor que 1 anda mais devagar.
        _moveDirection = direction.LengthSquared() > 1f ? Vector2.Normalize(direction) : direction;
        // Como no Factorio: andar interrompe a coleta; e sai do posto da máquina. A purificação à mão só pausa.
        if (_moveDirection != Vector2.Zero)
        {
            StopGathering();
            LeavePost();
        }
    }

    internal void StartGathering(SimWorld world, GridPos cell)
    {
        ResourceNode? node = world.GatherableAt(cell);
        if (node is null)
        {
            // Margem livre: cava argila (não esgota; docs/linha_aldeoes.md).
            if (Stats.Dig is not null && world.IsBank(cell) && world.BuildingAt(cell) is null && CanGather(cell))
            {
                StopGathering();
                DigCell = cell;
            }
            return;
        }
        if (!CanGather(cell, node.Shape))
            return;
        DigCell = null;
        if (node != GatherTarget)
            _gatherTicks = 0;
        GatherTarget = node;
    }

    internal void Tick(SimWorld world)
    {
        PreviousPosition = Position;
        if (_moveDirection != Vector2.Zero)
        {
            Move(world);
            return;
        }
        Gather();
        Dig();
        TickHand(world);
    }

    /// <summary>Põe mais uma receita à mão na fila (purificar, moldar); id desconhecido não faz nada.</summary>
    internal void QueueHandCraft(string id)
    {
        if (Stats.HandRecipes is not null && Stats.HandRecipes.TryGetValue(id, out HandRecipe? recipe))
            _handQueue.Enqueue(recipe);
    }

    /// <summary>
    /// Receitas à mão, uma de cada vez, só com ela parada: começa a próxima da fila se tiver as entradas (senão a tira da
    /// fila); a que precisa de água perto (moldar) espera ela chegar a até a distância pedida, e pausa longe dela.
    /// </summary>
    private void TickHand(SimWorld world)
    {
        HandRecipe? next = HandCurrent ?? (_handQueue.Count > 0 ? _handQueue.Peek() : null);
        HandNeedsWater = next is { NearWater: > 0f } && !NearWater(world, next.NearWater);
        if (next is null || HandNeedsWater)
            return;
        if (HandCurrent is null)
        {
            _handQueue.Dequeue();
            if (!Inventory.TryRemove(next.Recipe.Inputs))
                return;
            HandCurrent = next;
            _handTicks = 0;
        }
        if (++_handTicks < next.Recipe.Ticks)
            return;
        Inventory.Add(next.Recipe.Outputs);
        HandCurrent = null;
        _handTicks = 0;
    }

    /// <summary>Se há água a até <paramref name="distance"/> células (centro a centro) dela.</summary>
    public bool NearWater(SimWorld world, float distance)
    {
        int r = (int)MathF.Ceiling(distance);
        int cx = (int)MathF.Round(Position.X), cz = (int)MathF.Round(Position.Y);
        for (int dx = -r; dx <= r; dx++)
        for (int dz = -r; dz <= r; dz++)
        {
            var cell = new GridPos(cx + dx, cz + dz);
            if (world.IsWater(cell) && Vector2.Distance(Position, new Vector2(cell.X, cell.Z)) <= distance + 1e-4f)
                return true;
        }
        return false;
    }

    /// <summary>Cavando a margem: 1 argila a cada tempo de escavação; a margem não esgota.</summary>
    private void Dig()
    {
        if (DigCell is not GridPos cell || Stats.Dig is not DigType dig)
            return;
        if (!CanGather(cell))
        {
            DigCell = null;
            return;
        }
        Vector2 toCell = new Vector2(cell.X, cell.Z) - Position;
        if (toCell.LengthSquared() > 1e-6f)
            Facing = Vector2.Normalize(toCell);
        if (++_digTicks < dig.Ticks)
            return;
        _digTicks = 0;
        Inventory.Add(dig.Item);
    }

    /// <summary>Assume o posto vago dessa máquina (índice <paramref name="slot"/>), virada para ela.</summary>
    internal void TakePost(Building building, int slot)
    {
        LeavePost();
        Post = building;
        building.CastellanSlot = slot;
        Vector2 toMachine = new Vector2(building.Cell.X, building.Cell.Z) - Position;
        if (toMachine != Vector2.Zero)
            Facing = Vector2.Normalize(toMachine);
    }

    /// <summary>Sai do posto em que está (E de novo, andar, ou a máquina foi desmontada).</summary>
    internal void LeavePost()
    {
        if (Post is null)
            return;
        Post.CastellanSlot = null;
        Post = null;
    }

    private void Move(SimWorld world)
    {
        Vector2 step = _moveDirection * (Stats.CellsPerSecond / SimClock.TicksPerSecond);
        var max = new Vector2(world.Grid.Width - 1, world.Grid.Height - 1);

        // Paredes (células cheias): um eixo por vez, e bater num eixo ainda deixa deslizar no outro.
        Vector2 start = Position;
        Vector2 tryX = Vector2.Clamp(Position + new Vector2(step.X, 0f), Vector2.Zero, max);
        if (!Collides(world, tryX))
            Position = tryX;
        Vector2 tryZ = Vector2.Clamp(Position + new Vector2(0f, step.Y), Vector2.Zero, max);
        if (!Collides(world, tryZ))
            Position = tryZ;
        // Recursos (círculos: tronco, pedra, veio): anda e é empurrada para fora, então desliza em volta e passa no vão
        // entre dois vizinhos. Se o empurrão a jogar numa parede, ou se o vão for mais estreito que o corpo (sobra
        // sobreposição), fica onde estava.
        Vector2 pushed = Vector2.Clamp(world.PushOutOfTrunks(Position, Stats.Radius), Vector2.Zero, max);
        Position = Collides(world, pushed) || world.OverlapsResourceCircle(pushed, Stats.Radius) ? start : pushed;
        AssistAroundResource(world, start, step, max);

        Facing = Vector2.Normalize(_moveDirection);
    }

    /// <summary>
    /// De frente contra uma face reta de pedra (ou um tronco), o empurrão pela normal quase não deixa avançar: parece
    /// enroscar. Se ela avançou menos de 35% do passo e há um recurso encostado, tenta o passo desviado 35° e 60°,
    /// primeiro para o lado em que ela já está em relação ao centro da forma, e fica com o primeiro que a desloca sem
    /// recuar nem invadir nada: desliza pela face e contorna a quina mais perto sozinha. Só vale para recursos; em construções e na borda do mapa, não.
    /// </summary>
    private void AssistAroundResource(SimWorld world, Vector2 start, Vector2 step, Vector2 max)
    {
        float length = step.Length();
        if (length < 1e-6f)
            return;
        Vector2 dir = step / length;
        if (Vector2.Dot(Position - start, dir) >= 0.35f * length)
            return;
        if (world.NearestShape(start, Stats.Radius + length + 0.05f) is not (ResourceShape shape, Vector2 _))
            return;
        Vector2 center = shape.Centroid;
        var perp = new Vector2(-dir.Y, dir.X);
        float side = Vector2.Dot(start - center, perp) >= 0f ? 1f : -1f;
        foreach (float degrees in new[] { 35f * side, 60f * side, -35f * side, -60f * side })
        {
            float a = degrees * MathF.PI / 180f;
            var turned = new Vector2(dir.X * MathF.Cos(a) - dir.Y * MathF.Sin(a), dir.X * MathF.Sin(a) + dir.Y * MathF.Cos(a));
            Vector2 candidate = Vector2.Clamp(world.PushOutOfTrunks(start + turned * length, Stats.Radius), Vector2.Zero, max);
            if (Collides(world, candidate) || world.OverlapsResourceCircle(candidate, Stats.Radius))
                continue;
            // Deslizar ao longo da face conta, mesmo sem avançar na direção pedida (depois da quina volta a avançar).
            if ((candidate - start).Length() > 0.3f * length && Vector2.Dot(candidate - start, dir) > -0.01f * length)
            {
                Position = candidate;
                return;
            }
        }
    }

    /// <summary>Se o corpo, onde está agora, invade a célula (para não construir em cima dele).</summary>
    public bool BodyOverlaps(GridPos cell) => CircleHitsCell(Position + new Vector2(0.5f, 0.5f), cell);

    private bool CircleHitsCell(Vector2 center, GridPos cell)
    {
        var nearest = new Vector2(Math.Clamp(center.X, cell.X, cell.X + 1), Math.Clamp(center.Y, cell.Z, cell.Z + 1));
        return Vector2.DistanceSquared(center, nearest) < Stats.Radius * Stats.Radius;
    }

    /// <summary>
    /// Círculo do corpo contra as células cheias em volta (construções sólidas, pedra, veio, borda do mapa). Os troncos
    /// não entram aqui: são resolvidos por <see cref="SimWorld.PushOutOfTrunks"/>, que faz deslizar em volta deles.
    /// </summary>
    private bool Collides(SimWorld world, Vector2 position)
    {
        // Centro do corpo em coordenadas de borda de célula: a célula x ocupa [x, x+1].
        Vector2 center = position + new Vector2(0.5f, 0.5f);
        float r = Stats.Radius;
        for (int x = (int)MathF.Floor(center.X - r); x <= (int)MathF.Floor(center.X + r); x++)
        for (int z = (int)MathF.Floor(center.Y - r); z <= (int)MathF.Floor(center.Y + r); z++)
        {
            var cell = new GridPos(x, z);
            if (world.IsSolid(cell) && world.ShapeAt(cell) is null && CircleHitsCell(center, cell))
                return true;
        }
        return false;
    }

    private void Gather()
    {
        ResourceNode? node = GatherTarget;
        if (node is null)
            return;
        if (node.IsDepleted || !CanGather(node.Cell, node.Shape))
        {
            StopGathering();
            return;
        }

        Vector2 toNode = new Vector2(node.Cell.X, node.Cell.Z) - Position;
        if (toNode != Vector2.Zero)
            Facing = Vector2.Normalize(toNode);

        _gatherTicks++;
        if (_gatherTicks < node.Type.GatherTicks)
            return;

        _gatherTicks = 0;
        if (node.TakeOne())
            Inventory.Add(node.Kind);
        if (node.IsDepleted)
            StopGathering();
    }

    private void StopGathering()
    {
        GatherTarget = null;
        DigCell = null;
        _digTicks = 0;
        _gatherTicks = 0;
    }
}
