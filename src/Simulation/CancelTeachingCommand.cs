namespace Cidadela.Simulation;

/// <summary>Descarta a gravação em andamento.</summary>
public sealed record CancelTeachingCommand : ISimCommand
{
    public void Apply(SimWorld world) => world.CancelTeaching();
}
