using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>Receita de uma máquina, vinda de data/recipes.json: consome as entradas e, após o tempo, dá as saídas.</summary>
public sealed record RecipeType(
    string Id, string Machine, IReadOnlyDictionary<string, int> Inputs, IReadOnlyDictionary<string, int> Outputs, int Ticks);
