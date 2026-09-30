namespace Cidadela.Simulation;

/// <summary>Durante a gravação, marca "ir até" a célula onde a protagonista está (tecla G; docs/ladainhas.md, Q11).</summary>
public sealed record MarkGoToCommand : ISimCommand
{
    public void Apply(SimWorld world) => world.RecordGoToHere();
}
