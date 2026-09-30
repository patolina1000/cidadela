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
    /// Se está perto o bastante para coletar a célula: do centro do corpo até a borda da célula; se o recurso tem tronco
    /// (<paramref name="trunkRadius"/>), até a superfície do tronco. Encostado de lado ou na diagonal conta; uma célula
    /// de folga já não.
    /// </summary>
    public bool CanGather(GridPos cell, float? trunkRadius = null)
    {
        Vector2 center = Position + new Vector2(0.5f, 0.5f);
        if (trunkRadius is float t)
            return Vector2.Distance(center, new Vector2(cell.X + 0.5f, cell.Z + 0.5f)) - t <= Stats.GatherTrunkReach;
        var nearest = new Vector2(Math.Clamp(center.X, cell.X, cell.X + 1), Math.Clamp(center.Y, cell.Z, cell.Z + 1));
        return Vector2.Distance(center, nearest) <= Stats.GatherReach;
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
        if (node is null || !CanGather(cell, node.Type.TrunkRadius))
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

        // Um eixo por vez: bater numa parede num eixo ainda deixa deslizar no outro.
        Vector2 tryX = Vector2.Clamp(Position + new Vector2(step.X, 0f), Vector2.Zero, max);
        if (!Collides(world, tryX))
            Position = tryX;
        Vector2 tryZ = Vector2.Clamp(Position + new Vector2(0f, step.Y), Vector2.Zero, max);
        if (!Collides(world, tryZ))
            Position = tryZ;

        Facing = Vector2.Normalize(_moveDirection);
    }

    /// <summary>Se o corpo, onde está agora, invade a célula (para não construir em cima dele).</summary>
    public bool BodyOverlaps(GridPos cell) => CircleHitsCell(Position + new Vector2(0.5f, 0.5f), cell);

    private bool CircleHitsCell(Vector2 center, GridPos cell)
    {
        var nearest = new Vector2(Math.Clamp(center.X, cell.X, cell.X + 1), Math.Clamp(center.Y, cell.Z, cell.Z + 1));
        return Vector2.DistanceSquared(center, nearest) < Stats.Radius * Stats.Radius;
    }

    /// <summary>
    /// Círculo do corpo contra o que bloqueia em volta: o quadrado da célula sólida ou, se o recurso tem tronco, só o
    /// círculo do tronco no centro da célula (dá para chegar perto do pé da árvore e passar sob a copa).
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
            if (!world.IsSolid(cell))
                continue;
            if (world.ResourceAt(cell)?.Type.TrunkRadius is float t)
            {
                if (Vector2.Distance(center, new Vector2(x + 0.5f, z + 0.5f)) < r + t)
                    return true;
            }
            else if (CircleHitsCell(center, cell))
                return true;
        }
        return false;
    }

    private void Gather()
    {
        ResourceNode? node = GatherTarget;
        if (node is null)
            return;
        if (node.IsDepleted || !CanGather(node.Cell, node.Type.TrunkRadius))
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
