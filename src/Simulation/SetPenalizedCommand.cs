namespace Cidadela.Simulation;

/// <summary>
/// Liga ou desliga em todos os aldeões a penalidade de velocidade (fome ou moral baixa), por enquanto só como
/// tecla de depuração: fome e moral ainda não existem na simulação; quando existirem, elas chamam
/// <see cref="Villager.SetPenalized"/> direto.
/// </summary>
public sealed record SetPenalizedCommand(bool Penalized) : ISimCommand
{
    public void Apply(SimWorld world)
    {
        foreach (Villager villager in world.Villagers)
            villager.SetPenalized(Penalized);
    }
}
