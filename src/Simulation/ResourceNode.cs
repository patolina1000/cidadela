namespace Cidadela.Simulation;

/// <summary>Fonte de recurso bruto no mapa (madeira, pedra, ferro). Some quando esgota.</summary>
public sealed class ResourceNode
{
    public int Id { get; }
    public ResourceType Type { get; }
    public GridPos Cell { get; }
    public int Remaining { get; private set; }

    /// <summary>Índice da variação sorteada (em <see cref="ResourceType.Variants"/>), fixo pela célula; 0 sem variações.</summary>
    public int Variant { get; }

    /// <summary>Escala sorteada (fixa pela célula); a cena desenha o modelo nela.</summary>
    public float Scale { get; }

    /// <summary>Giro em Y (radianos), fixo pela célula: a cena desenha o modelo nele e a forma de bloqueio gira junto.</summary>
    public float Yaw { get; }

    /// <summary>O que bloqueia no chão, já girado, escalado e na célula; null = bloqueia a célula inteira.</summary>
    public ResourceShape? Shape { get; }

    public string Kind => Type.Kind;
    public bool IsDepleted => Remaining <= 0;

    public ResourceNode(int id, ResourceType type, GridPos cell)
    {
        Id = id;
        Type = type;
        Cell = cell;
        Remaining = type.StartAmount;
        uint h = CellHash.Of(cell.X, cell.Z);
        Variant = Pick(type.Variants, CellHash.Unit(h));
        Scale = type.MinScale + (type.MaxScale - type.MinScale) * CellHash.Unit(CellHash.Mix(h, 2));
        Yaw = CellHash.Unit(CellHash.Mix(h, 1)) * 2f * System.MathF.PI;
        Shape = type.Variants.Count > 0
            ? type.Variants[Variant].Shape.Placed(new System.Numerics.Vector2(cell.X, cell.Z), Yaw, Scale)
            : null;
    }

    private static int Pick(System.Collections.Generic.IReadOnlyList<ResourceVariant> variants, float r)
    {
        float total = 0f;
        foreach (ResourceVariant v in variants)
            total += v.Weight;
        float acc = 0f;
        for (int i = 0; i < variants.Count; i++)
        {
            acc += variants[i].Weight / total;
            if (r < acc)
                return i;
        }
        return System.Math.Max(0, variants.Count - 1);
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
