using System.Collections.Generic;
using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>
/// Aldeão que patrulha uma rota de células em loop. Existe por enquanto para provar
/// que a simulação anda em ticks e a cena só desenha.
/// </summary>
public sealed class Villager
{
    public int Id { get; }

    /// <summary>Posição contínua no plano da grade (X, Z), em células.</summary>
    public Vector2 Position { get; private set; }

    /// <summary>Posição no tick anterior, para a cena interpolar.</summary>
    public Vector2 PreviousPosition { get; private set; }

    private readonly IReadOnlyList<GridPos> _path;
    private readonly float _cellsPerTick;
    private int _targetIndex;

    public Villager(int id, IReadOnlyList<GridPos> path, float cellsPerSecond)
    {
        Id = id;
        _path = path;
        _cellsPerTick = cellsPerSecond / SimClock.TicksPerSecond;
        Position = ToVector(path[0]);
        PreviousPosition = Position;
        _targetIndex = path.Count > 1 ? 1 : 0;
    }

    internal void Tick()
    {
        PreviousPosition = Position;
        float budget = _cellsPerTick;
        while (budget > 0f && _path.Count > 1)
        {
            Vector2 target = ToVector(_path[_targetIndex]);
            Vector2 toTarget = target - Position;
            float distance = toTarget.Length();
            if (distance > budget)
            {
                Position += toTarget / distance * budget;
                return;
            }
            Position = target;
            budget -= distance;
            _targetIndex = (_targetIndex + 1) % _path.Count;
        }
    }

    private static Vector2 ToVector(GridPos cell) => new(cell.X, cell.Z);
}
