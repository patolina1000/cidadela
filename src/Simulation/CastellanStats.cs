namespace Cidadela.Simulation;

/// <summary>
/// Atributos do Castelão (data/castellan.json). GatherSurfaceReach: alcance de coleta até a borda do círculo que o recurso
/// bloqueia (o tronco da árvore, a base da pedra ou do veio). PurifyByHand: a receita que só ela faz com as mãos
/// (docs/linha_energia.md: 2 podres → 1 puro em 6 s, sem água), ou null.
/// </summary>
public sealed record CastellanStats(float CellsPerSecond, float Reach, float GatherReach, float Radius, float GatherSurfaceReach = 1.3f,
    RecipeType? PurifyByHand = null);
