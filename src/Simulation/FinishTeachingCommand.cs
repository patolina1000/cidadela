namespace Cidadela.Simulation;

/// <summary>"Pronto": entrega o que foi gravado ao aldeão (ele recusa o que não cabe na Inteligência dele).</summary>
public sealed record FinishTeachingCommand : ISimCommand
{
    public void Apply(SimWorld world) => world.FinishTeaching();
}
