namespace Cidadela.Simulation;

/// <summary>Construir um tipo numa célula, virado para uma direção. Só acontece se <see cref="SimWorld.CanBuild"/> deixar.</summary>
public sealed record BuildCommand(string Kind, GridPos Cell, Direction Direction) : ISimCommand
{
    public void Apply(SimWorld world) => world.TryBuild(Kind, Cell, Direction);
}
