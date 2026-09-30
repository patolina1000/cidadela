namespace Cidadela.Simulation;

/// <summary>
/// Definição de um item, vinda de data/items.json. A cor é hex (sem #), para a cena desenhar.
/// <paramref name="Weight"/>: pesado (só nas costas) ou leve (esteira e mariposa).
/// </summary>
public sealed record ItemType(string Kind, string Name, string Color, ItemWeight Weight)
{
    public bool IsHeavy => Weight == ItemWeight.Heavy;
}
