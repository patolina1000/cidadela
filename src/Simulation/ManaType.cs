namespace Cidadela.Simulation;

/// <summary>
/// Mana de uma construção ("mana" em data/buildings.json; docs/linha_energia.md), em mana por segundo.
/// <paramref name="Use"/>: quanto gasta trabalhando; <paramref name="IdleUse"/>: quanto gasta parada (a mariposa);
/// <paramref name="Supply"/>: quanto gera (o Relicário, enquanto queima). A sobra da rede se perde (o Cristal-mãe deixou de
/// guardar mana: ele gasta formando aldeões, docs/linha_aldeoes.md, L2 do Arthur).
/// </summary>
public sealed record ManaType(float Use = 0f, float IdleUse = 0f, float Supply = 0f);
