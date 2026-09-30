namespace Cidadela.Simulation;

/// <summary>
/// Mana de uma construção ("mana" em data/buildings.json; docs/linha_energia.md), em mana por segundo.
/// <paramref name="Use"/>: quanto gasta trabalhando; <paramref name="IdleUse"/>: quanto gasta parada (a mariposa);
/// <paramref name="Supply"/>: quanto gera (o Relicário, enquanto queima); <paramref name="Capacity"/>: quanto guarda
/// (o Cristal-mãe, que só recebe a sobra da rede).
/// </summary>
public sealed record ManaType(float Use = 0f, float IdleUse = 0f, float Supply = 0f, float Capacity = 0f);
