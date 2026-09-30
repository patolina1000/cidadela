namespace Cidadela.Simulation;

/// <summary>
/// Postos de trabalho de uma construção ("posts" em data/buildings.json): quantos aldeões ela
/// precisa encostados para andar, o nome do ofício e a ferramenta (o ícone sobre a cabeça de quem está no posto).
/// </summary>
public sealed record PostType(int Count, string Name, string Tool);
