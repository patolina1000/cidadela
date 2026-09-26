using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>Itens carregados, por tipo. Ainda sem limite de espaço.</summary>
public sealed class Inventory
{
    private readonly Dictionary<string, int> _counts = new();

    public IReadOnlyDictionary<string, int> Counts => _counts;

    public int Count(string kind) => _counts.GetValueOrDefault(kind);

    internal void Add(string kind, int amount = 1) => _counts[kind] = Count(kind) + amount;

    public bool Has(IReadOnlyDictionary<string, int> items)
    {
        foreach ((string kind, int amount) in items)
            if (Count(kind) < amount)
                return false;
        return true;
    }

    internal void Add(IReadOnlyDictionary<string, int> items)
    {
        foreach ((string kind, int amount) in items)
            Add(kind, amount);
    }

    /// <summary>Tira os itens se tiver todos; senão não tira nada.</summary>
    internal bool TryRemove(IReadOnlyDictionary<string, int> items)
    {
        if (!Has(items))
            return false;
        foreach ((string kind, int amount) in items)
            _counts[kind] = Count(kind) - amount;
        return true;
    }
}
