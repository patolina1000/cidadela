namespace Cidadela.Simulation;

/// <summary>Construção colocada numa célula (esteira, baú, máquina). Ainda sem funcionamento.</summary>
public sealed class Building
{
    public int Id { get; }
    public BuildingType Type { get; }
    public GridPos Cell { get; }
    public Direction Direction { get; }

    public string Kind => Type.Kind;

    public Building(int id, BuildingType type, GridPos cell, Direction direction)
    {
        Id = id;
        Type = type;
        Cell = cell;
        Direction = direction;
    }
}
