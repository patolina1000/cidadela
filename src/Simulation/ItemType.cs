namespace Cidadela.Simulation;

/// <summary>
/// Definição de um item, vinda de data/items.json. A cor é hex (sem #), para a cena desenhar.
/// <paramref name="Raw"/>: item bruto (tora, pedra, minério): não entra em esteira, só anda nas costas de alguém.
/// </summary>
public sealed record ItemType(string Kind, string Name, string Color, bool Raw = false);
