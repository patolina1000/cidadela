using System;

namespace Cidadela.Simulation;

/// <summary>Direção numa célula. Norte = -Z, leste = +X, sul = +Z, oeste = -X.</summary>
public enum Direction
{
    North,
    East,
    South,
    West,
}

public static class DirectionExtensions
{
    /// <summary>As quatro direções, em ordem.</summary>
    public static readonly Direction[] All = { Direction.North, Direction.East, Direction.South, Direction.West };

    public static Direction RotatedClockwise(this Direction d) => (Direction)(((int)d + 1) % 4);

    public static Direction Opposite(this Direction d) => (Direction)(((int)d + 2) % 4);

    /// <summary>Vetor unitário no plano (X, Z).</summary>
    public static System.Numerics.Vector2 ToVector(this Direction d) => d switch
    {
        Direction.North => new System.Numerics.Vector2(0f, -1f),
        Direction.East => new System.Numerics.Vector2(1f, 0f),
        Direction.South => new System.Numerics.Vector2(0f, 1f),
        Direction.West => new System.Numerics.Vector2(-1f, 0f),
        _ => throw new ArgumentOutOfRangeException(nameof(d)),
    };

    /// <summary>A célula vizinha nessa direção.</summary>
    public static GridPos Step(this GridPos cell, Direction d) => d switch
    {
        Direction.North => new GridPos(cell.X, cell.Z - 1),
        Direction.East => new GridPos(cell.X + 1, cell.Z),
        Direction.South => new GridPos(cell.X, cell.Z + 1),
        Direction.West => new GridPos(cell.X - 1, cell.Z),
        _ => throw new ArgumentOutOfRangeException(nameof(d)),
    };

    public static Direction Parse(string? text) => text?.ToLowerInvariant() switch
    {
        null or "" or "north" => Direction.North,
        "east" => Direction.East,
        "south" => Direction.South,
        "west" => Direction.West,
        _ => throw new FormatException($"Direção desconhecida: \"{text}\"."),
    };
}
