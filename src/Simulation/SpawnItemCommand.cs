namespace Cidadela.Simulation;

/// <summary>
/// Faz nascer 1 item na entrada de uma esteira, sem Castelão nem alcance: é o alimentador do palco da
/// Biografia (máquinas trabalhando de verdade) e de cenas de teste. Sem esteira na célula, ou sem espaço
/// na entrada, não faz nada.
/// </summary>
public sealed record SpawnItemCommand(GridPos Cell, string Kind) : ISimCommand
{
    public void Apply(SimWorld world) => world.TrySpawnItem(Cell, Kind);
}
