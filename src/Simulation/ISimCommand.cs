namespace Cidadela.Simulation;

/// <summary>
/// Pedido de mudança vindo de fora da simulação (entrada do jogador).
/// Fica na fila e só é aplicado no começo do próximo tick.
/// </summary>
public interface ISimCommand
{
    void Apply(SimWorld world);
}
