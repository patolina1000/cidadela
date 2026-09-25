namespace Cidadela.Simulation;

/// <summary>Fonte de recurso bruto no mapa (madeira, pedra, ferro).</summary>
public sealed record ResourceNode(int Id, string Kind, GridPos Cell);
