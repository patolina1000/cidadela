namespace Cidadela.Simulation;

/// <summary>
/// Põe mais uma receita à mão na fila da protagonista ("purify" com P, "mold" com M; data/castellan.json, handRecipes).
/// </summary>
public sealed record HandCraftCommand(string Recipe) : ISimCommand
{
    public void Apply(SimWorld world) => world.Castellan.QueueHandCraft(Recipe);
}
