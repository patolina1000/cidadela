namespace Cidadela.Simulation;

/// <summary>Começa a gravar uma ladainha para o aldeão (docs/ladainhas.md, "Ensinar": a protagonista escolhe e aperta Ensinar).</summary>
public sealed record StartTeachingCommand(int VillagerId) : ISimCommand
{
    public void Apply(SimWorld world) => world.StartTeaching(VillagerId);
}
