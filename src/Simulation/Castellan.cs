using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>
/// O personagem principal (GDD, seção 20). Anda na direção pedida pelo último
/// <see cref="MoveCommand"/>, a uma velocidade fixa por tick, sem sair do mapa.
/// </summary>
public sealed class Castellan
{
    public int Id { get; }

    /// <summary>Posição contínua no plano da grade (X, Z), em células.</summary>
    public Vector2 Position { get; private set; }

    /// <summary>Posição no tick anterior, para a cena interpolar.</summary>
    public Vector2 PreviousPosition { get; private set; }

    /// <summary>Direção para onde está virado (unitária). Só muda quando anda.</summary>
    public Vector2 Facing { get; private set; } = new(0f, 1f);

    public float CellsPerSecond { get; }

    private Vector2 _moveDirection;

    public Castellan(int id, Vector2 position, float cellsPerSecond)
    {
        Id = id;
        Position = position;
        PreviousPosition = position;
        CellsPerSecond = cellsPerSecond;
    }

    internal void SetMoveDirection(Vector2 direction)
    {
        // Diagonal não pode ser mais rápida; entrada analógica menor que 1 anda mais devagar.
        _moveDirection = direction.LengthSquared() > 1f ? Vector2.Normalize(direction) : direction;
    }

    internal void Tick(WorldGrid grid)
    {
        PreviousPosition = Position;
        if (_moveDirection == Vector2.Zero)
            return;

        Vector2 next = Position + _moveDirection * (CellsPerSecond / SimClock.TicksPerSecond);
        Position = Vector2.Clamp(next, Vector2.Zero, new Vector2(grid.Width - 1, grid.Height - 1));
        Facing = Vector2.Normalize(_moveDirection);
    }
}
