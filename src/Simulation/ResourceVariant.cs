namespace Cidadela.Simulation;

/// <summary>
/// Variação de um recurso (data/resources.json, na ordem das variações do manifesto do cenário): peso do sorteio e raio,
/// em metros, do círculo que bloqueia no centro da célula (o tronco da árvore, a base da pedra ou do veio).
/// </summary>
public sealed record ResourceVariant(float Weight, float Radius);
