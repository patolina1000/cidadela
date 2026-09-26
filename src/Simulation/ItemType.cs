namespace Cidadela.Simulation;

/// <summary>Definição de um item, vinda de data/items.json. A cor é hex (sem #), para a cena desenhar.</summary>
public sealed record ItemType(string Kind, string Name, string Color);
