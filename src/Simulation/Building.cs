namespace Cidadela.Simulation;

/// <summary>Construção colocada numa célula (esteira, baú, máquina). Máquinas ainda não produzem.</summary>
public sealed class Building
{
    public int Id { get; }
    public BuildingType Type { get; }
    public GridPos Cell { get; }
    public Direction Direction { get; }

    /// <summary>Itens andando nesta esteira, ou null se não é esteira.</summary>
    public BeltLane? Belt { get; }

    /// <summary>Itens guardados, ou null se não guarda (só baú).</summary>
    public Inventory? Storage { get; }

    public string Kind => Type.Kind;

    public Building(int id, BuildingType type, GridPos cell, Direction direction)
    {
        Id = id;
        Type = type;
        Cell = cell;
        Direction = direction;
        if (type.IsBelt)
            Belt = new BeltLane();
        if (type.Storage)
            Storage = new Inventory();
    }
}
