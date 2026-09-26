using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>Definição de uma construção, vinda de data/buildings.json.</summary>
public sealed record BuildingType(string Kind, string Name, IReadOnlyDictionary<string, int> Cost, bool Solid);
