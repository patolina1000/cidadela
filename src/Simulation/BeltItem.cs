using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>Um item andando numa esteira.</summary>
public sealed class BeltItem
{
    public int Id { get; }
    public string Kind { get; }

    /// <summary>Quanto já andou na esteira atual: 0 = entrada, 1 = saída.</summary>
    public float Progress { get; internal set; }

    /// <summary>Posição no plano da grade (mesma convenção do Castelão: (x, z) = centro da célula x, z).</summary>
    public Vector2 Position { get; internal set; }

    /// <summary>Posição no tick anterior, para a cena interpolar (inclusive ao trocar de esteira).</summary>
    public Vector2 PreviousPosition { get; internal set; }

    public BeltItem(int id, string kind)
    {
        Id = id;
        Kind = kind;
    }
}
