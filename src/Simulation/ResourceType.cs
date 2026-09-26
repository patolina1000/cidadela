namespace Cidadela.Simulation;

/// <summary>Definição de um recurso bruto, vinda de data/resources.json.</summary>
public sealed record ResourceType(string Kind, string Name, int GatherTicks, int StartAmount);
