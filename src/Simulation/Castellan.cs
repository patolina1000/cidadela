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
    public CastellanStats Stats { get; }
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

    private Vector2 _moveDirection;
    private int _gatherTicks;

    public Castellan(int id, Vector2 position, CastellanStats stats)
    {
        Id = id;
        Position = position;
        PreviousPosition = position;
        Stats = stats;
    }

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
        // Como no Factorio: andar interrompe o trabalho manual.
        if (_moveDirection != Vector2.Zero)
            StopGathering();
    }

    internal void StartGathering(SimWorld world, GridPos cell)
    {
        ResourceNode? node = world.ResourceAt(cell);
        if (node is null || !CanGather(cell, node.Shape))
            return;
        if (node != GatherTarget)
            _gatherTicks = 0;
        GatherTarget = node;
    }

    internal void Tick(SimWorld world)
    {
        PreviousPosition = Position;
        if (_moveDirection != Vector2.Zero)
            Move(world);
        else
            Gather();
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
        _gatherTicks = 0;
    }
}
