namespace Cidadela.Simulation;

/// <summary>
/// Até quando "operar" dura (docs/ladainhas.md: "Operar [máquina] até [ficar sem insumo ou com a saída cheia]").
/// </summary>
public enum OperateUntil
{
    /// <summary>Até a máquina parar por qualquer um dos dois (o que a demonstração grava).</summary>
    Either,
    /// <summary>Até faltar insumo (com a saída cheia também para: a máquina não anda).</summary>
    NoInput,
    /// <summary>Até a saída encher (ou a máquina esgotar o veio): espera no posto enquanto falta insumo.</summary>
    OutputFull,
}
