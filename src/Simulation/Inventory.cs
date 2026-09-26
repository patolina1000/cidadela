using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>Itens carregados, por tipo. Ainda sem limite de espaço.</summary>
public sealed class Inventory
{
    private readonly Dictionary<string, int> _counts = new();

    public IReadOnlyDictionary<string, int> Counts => _counts;

    public int Count(string kind) => _counts.GetValueOrDefault(kind);

    internal void Add(string kind, int amount = 1) => _counts[kind] = Count(kind) + amount;
}
