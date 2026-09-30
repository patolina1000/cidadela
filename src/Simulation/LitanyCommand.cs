namespace Cidadela.Simulation;

/// <summary>
/// Um comando de ladainha. <paramref name="Item"/>: o item (pegar, pôr); <paramref name="Target"/>: onde;
/// <paramref name="Ticks"/>: quanto esperar (só "esperar"); <paramref name="Until"/>: até quando "operar" dura.
/// </summary>
public sealed record LitanyCommand(LitanyVerb Verb, LitanyTarget? Target = null, string? Item = null, int Ticks = 0,
    OperateUntil Until = OperateUntil.Either)
{
    /// <summary>Inteligência mínima para entender este comando (todos da versão 1 pedem 1).</summary>
    public int RequiredIntelligence => 1;
}
