namespace Cidadela.Simulation;

/// <summary>
/// Receita que só a protagonista faz com as mãos ("handRecipes" em data/castellan.json): purificar (2 podres → 1 puro) e
/// moldar a casca (2 argilas → 1 casca). <paramref name="NearWater"/> &gt; 0: só anda com ela a até essa distância (centro a
/// centro, em células) de uma célula de água.
/// </summary>
public sealed record HandRecipe(RecipeType Recipe, float NearWater = 0f);
