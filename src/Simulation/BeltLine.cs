using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Uma linha de esteira (docs/cadeia_flecha.md): as esteiras ligadas pelo fluxo (uma apontando para a outra). Na era do
/// torque ela só anda com manivelas ativas que cubram o tamanho dela: cada manivela (aldeão no posto ou eixo girando)
/// move até <see cref="BuildingType.CrankCells"/> células.
/// </summary>
public sealed class BeltLine
{
    public List<Building> Belts { get; } = new();

    /// <summary>Manivelas que apontam para uma esteira desta linha.</summary>
    public List<Building> Cranks { get; } = new();

    public int Length => Belts.Count;

    /// <summary>Quantas células as manivelas ativas movem agora (a simulação atualiza a cada tick).</summary>
    public int Capacity { get; internal set; }

    /// <summary>Se a linha anda neste tick.</summary>
    public bool Moving { get; internal set; }

    /// <summary>Se precisa de manivela (esteira da era do torque); falso = anda sempre (testes antigos, vitrine).</summary>
    public bool NeedsPower { get; internal set; }
}
