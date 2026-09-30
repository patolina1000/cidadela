namespace Cidadela.Simulation;

/// <summary>
/// Variação de um recurso (data/resources.json, na ordem das variações do manifesto do cenário): peso do sorteio e a forma
/// que bloqueia no chão, em coordenadas do modelo (o tronco da árvore, a base da pedra ou do veio).
/// </summary>
public sealed record ResourceVariant(float Weight, ResourceShape Shape);
