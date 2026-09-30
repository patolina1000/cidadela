namespace Cidadela.Simulation;

/// <summary>P: põe mais uma purificação à mão na fila da protagonista (2 podres → 1 puro em 6 s, sem água; só ela faz).</summary>
public sealed record PurifyByHandCommand : ISimCommand
{
    public void Apply(SimWorld world) => world.Castellan.QueuePurify();
}
