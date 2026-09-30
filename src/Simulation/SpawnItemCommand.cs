namespace Cidadela.Simulation;

/// <summary>
/// Põe 1 item direto na entrada da máquina (ou no baú) da célula, sem Castelão nem alcance: é o alimentador do palco da
/// Biografia (máquinas trabalhando de verdade) e de testes.
/// </summary>
public sealed record SpawnItemCommand(GridPos Cell, string Kind) : ISimCommand
{
    public void Apply(SimWorld world) => world.TrySpawnItem(Cell, Kind);
}
