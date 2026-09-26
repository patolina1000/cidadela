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
    public static Direction RotatedClockwise(this Direction d) => (Direction)(((int)d + 1) % 4);

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
