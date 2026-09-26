namespace Cidadela.Simulation;

/// <summary>O Castelão recolhe tudo o que o baú guarda, dentro do alcance.</summary>
public sealed record TakeFromChestCommand(GridPos Cell) : ISimCommand
{
    public void Apply(SimWorld world) => world.TryTakeFromChest(Cell);
}
