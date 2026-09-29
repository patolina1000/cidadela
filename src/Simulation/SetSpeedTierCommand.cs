namespace Cidadela.Simulation;

/// <summary>
/// Põe todos os aldeões num patamar de velocidade (tecla de depuração). Quando existir o mecanismo de
/// pesquisa ou era que libera os patamares, ele deve mudar o patamar por aqui também, em vez da view.
/// </summary>
public sealed record SetSpeedTierCommand(int Tier) : ISimCommand
{
    public void Apply(SimWorld world)
    {
        foreach (Villager villager in world.Villagers)
            villager.SetSpeedTier(Tier);
    }
}
