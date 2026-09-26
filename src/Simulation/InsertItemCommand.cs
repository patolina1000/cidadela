namespace Cidadela.Simulation;

/// <summary>O Castelão põe 1 item do inventário numa esteira (na entrada) ou num baú, dentro do alcance.</summary>
public sealed record InsertItemCommand(GridPos Cell, string Kind) : ISimCommand
{
    public void Apply(SimWorld world) => world.TryInsertItem(Cell, Kind);
}
