namespace Cidadela.Simulation;

/// <summary>Pede ao Castelão para coletar o recurso daquela célula (se houver e estiver no alcance).</summary>
public sealed record GatherCommand(GridPos Cell) : ISimCommand
{
    public void Apply(SimWorld world) => world.Castellan.StartGathering(world, Cell);
}
