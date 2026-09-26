namespace Cidadela.Simulation;

/// <summary>Desmontar a construção da célula, se estiver no alcance, devolvendo o custo ao Castelão.</summary>
public sealed record DeconstructCommand(GridPos Cell) : ISimCommand
{
    public void Apply(SimWorld world) => world.TryDeconstruct(Cell);
}
