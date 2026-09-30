namespace Cidadela.Simulation;

/// <summary>Atributos do Castelão, vindos de data/castellan.json.</summary>
/// <summary>Atributos do Castelão (data/castellan.json). GatherTrunkReach: alcance de coleta até a superfície do tronco.</summary>
public sealed record CastellanStats(float CellsPerSecond, float Reach, float GatherReach, float Radius, float GatherTrunkReach = 1.3f);
