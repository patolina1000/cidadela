namespace Cidadela.Simulation;

/// <summary>Se um aldeão aceita uma ladainha, e por que não (a interface diz o motivo; docs/ladainhas.md).</summary>
public enum LitanyFit
{
    Ok,
    /// <summary>Mais comandos do que a Inteligência dele guarda.</summary>
    TooLong,
    /// <summary>Um comando que a Inteligência dele não entende.</summary>
    TooHard,
    /// <summary>Ladainha vazia.</summary>
    Empty,
}
