namespace Cidadela.Simulation;

/// <summary>Máquina parada numa célula. Ainda sem receitas: só ocupa espaço.</summary>
public sealed record Machine(int Id, string Kind, GridPos Cell);
