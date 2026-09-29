using System;
using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Atributos dos aldeões, vindos de data/villagers.json (decisão de 29/09/2026: velocidade por patamares).
/// <paramref name="SpeedTiers"/>: base e melhorias, em células por segundo (o índice é o patamar);
/// <paramref name="PenaltyFactor"/>: multiplicador com fome ou moral baixa (no JSON vai a velocidade
/// resultante no patamar base, "penaltySpeed"); <paramref name="MaxSpeed"/>: teto da velocidade final.
/// Velocidade final = patamar × bônus do piso × penalidade, presa ao teto (<see cref="FinalSpeed"/>).
/// </summary>
public sealed record VillagerStats(IReadOnlyList<float> SpeedTiers, float PenaltyFactor, float MaxSpeed,
    float GatherMultiplier, int Carry)
{
    /// <summary>Velocidade do patamar base (índice 0).</summary>
    public float BaseSpeed => SpeedTiers[0];

    /// <summary>Velocidade final em células por segundo, pela fórmula da decisão de 29/09/2026.</summary>
    public float FinalSpeed(int tier, float floorBonus, bool penalized)
    {
        int index = Math.Clamp(tier, 0, SpeedTiers.Count - 1);
        float speed = SpeedTiers[index] * floorBonus * (penalized ? PenaltyFactor : 1f);
        return MathF.Min(speed, MaxSpeed);
    }
}
