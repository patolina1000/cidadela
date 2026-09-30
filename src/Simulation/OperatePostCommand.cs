namespace Cidadela.Simulation;

/// <summary>E: a protagonista assume o posto vago da máquina encostada nela, ou sai do posto em que está.</summary>
public sealed record OperatePostCommand : ISimCommand
{
    public void Apply(SimWorld world) => world.ToggleCastellanPost();
}
