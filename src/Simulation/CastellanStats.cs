namespace Cidadela.Simulation;

/// <summary>
/// Atributos do Castelão (data/castellan.json). GatherSurfaceReach: alcance de coleta até a borda do círculo que o recurso
/// bloqueia (o tronco da árvore, a base da pedra ou do veio). HandRecipes: o que só ela faz com as mãos, pelo id (purificar,
/// moldar a casca). Dig: cavar a margem (argila), ou null.
/// </summary>
public sealed record CastellanStats(float CellsPerSecond, float Reach, float GatherReach, float Radius, float GatherSurfaceReach = 1.3f,
    System.Collections.Generic.IReadOnlyDictionary<string, HandRecipe>? HandRecipes = null, DigType? Dig = null);
