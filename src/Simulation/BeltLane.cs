using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// A fila de itens de uma esteira, da frente (mais perto da saída) para trás.
/// Os itens mantêm pelo menos <see cref="Spacing"/> de distância, então cabem 3 por esteira.
/// </summary>
public sealed class BeltLane
{
    public const float Spacing = 0.5f;

    private readonly List<BeltItem> _items = new();

    public IReadOnlyList<BeltItem> Items => _items;

    /// <summary>Se cabe um item novo na entrada (progresso 0).</summary>
    public bool HasRoomAtEntry => _items.Count == 0 || _items[^1].Progress >= Spacing;

    internal void AddAtEntry(BeltItem item, float progress = 0f)
    {
        item.Progress = progress;
        _items.Add(item);
    }

    internal BeltItem RemoveFront()
    {
        BeltItem front = _items[0];
        _items.RemoveAt(0);
        return front;
    }

    internal void Clear() => _items.Clear();

    /// <summary>Anda todos para a frente, sem passar da saída nem encostar no da frente.</summary>
    internal void Advance(float step)
    {
        float limit = 1f;
        foreach (BeltItem item in _items)
        {
            item.Progress = System.MathF.Min(item.Progress + step, limit);
            limit = item.Progress - Spacing;
        }
    }
}
