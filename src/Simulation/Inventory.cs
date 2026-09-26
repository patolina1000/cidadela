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

    public bool IsEmpty
    {
        get
        {
            foreach (int amount in _counts.Values)
                if (amount > 0)
                    return false;
            return true;
        }
    }

    /// <summary>Passa tudo para outro inventário e fica vazio.</summary>
    internal void MoveAllTo(Inventory target)
    {
        foreach ((string kind, int amount) in _counts)
            if (amount > 0)
                target.Add(kind, amount);
        _counts.Clear();
    }

    /// <summary>Tira 1 item do tipo. Falso se não tinha.</summary>
    internal bool TryRemoveOne(string kind)
    {
        if (Count(kind) <= 0)
            return false;
        _counts[kind] = Count(kind) - 1;
        return true;
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
