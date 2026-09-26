namespace Cidadela.Simulation;

/// <summary>O Castelão recolhe tudo de um baú, ou a produção pronta de uma máquina, dentro do alcance.</summary>
public sealed record TakeAllCommand(GridPos Cell) : ISimCommand
{
    public void Apply(SimWorld world) => world.TryTakeAll(Cell);
}
