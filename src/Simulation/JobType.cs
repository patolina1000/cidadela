namespace Cidadela.Simulation;

/// <summary>Ofício de uma cabana de trabalho, vindo do "job" em data/buildings.json.</summary>
public sealed record JobType(string Name, string Resource, float Radius, int Capacity);
