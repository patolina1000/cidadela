namespace Cidadela.Simulation;

/// <summary>Atributos do Castelão, vindos de data/castellan.json.</summary>
/// <summary>
/// Atributos do Castelão (data/castellan.json). GatherSurfaceReach: alcance de coleta até a borda do círculo que o recurso
/// bloqueia (o tronco da árvore, a base da pedra ou do veio).
/// </summary>
public sealed record CastellanStats(float CellsPerSecond, float Reach, float GatherReach, float Radius, float GatherSurfaceReach = 1.3f);
