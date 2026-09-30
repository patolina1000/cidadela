namespace Cidadela.Simulation;

/// <summary>Os comandos de uma ladainha (docs/ladainhas.md). Todos da Inteligência 1.</summary>
public enum LitanyVerb
{
    /// <summary>Ir até [construção ou lugar].</summary>
    GoTo,
    /// <summary>Pegar [item] de [lugar] (baú, saída de máquina, cabana).</summary>
    Take,
    /// <summary>Pôr [item] em [lugar] (baú, entrada de máquina, cabana).</summary>
    Put,
    /// <summary>Colher, arrancar ou cavar [recurso] mais perto dentro de um raio.</summary>
    Gather,
    /// <summary>Operar [máquina] até ela ficar sem insumo ou com a saída cheia.</summary>
    Operate,
    /// <summary>Esperar [segundos].</summary>
    Wait,
}
