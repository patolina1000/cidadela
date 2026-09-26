namespace Cidadela.Simulation;

/// <summary>Fonte de recurso bruto no mapa (madeira, pedra, ferro). Some quando esgota.</summary>
public sealed class ResourceNode
{
    public int Id { get; }
    public ResourceType Type { get; }
    public GridPos Cell { get; }
    public int Remaining { get; private set; }

    public string Kind => Type.Kind;
    public bool IsDepleted => Remaining <= 0;

    public ResourceNode(int id, ResourceType type, GridPos cell)
    {
        Id = id;
        Type = type;
        Cell = cell;
        Remaining = type.StartAmount;
    }

    /// <summary>Tira 1 item. Falso se já estava esgotado.</summary>
    internal bool TakeOne()
    {
        if (IsDepleted)
            return false;
        Remaining--;
        return true;
    }
}
