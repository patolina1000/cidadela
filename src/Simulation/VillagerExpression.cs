namespace Cidadela.Simulation;

/// <summary>
/// Expressão do rosto do aldeão (GDD, "Aldeão: implementação v1"). A ordem é a das células do atlas 3×3
/// em assets/texturas/aldeao/expressoes.png (1 = distraído ... 9 = bravo), então o índice inteiro é a célula.
/// </summary>
public enum VillagerExpression
{
    /// <summary>Padrão: parado ou andando.</summary>
    Distracted,
    /// <summary>Carregando ou coletando.</summary>
    Effort,
    /// <summary>Acabou de entregar (ou subiu de nível, no futuro).</summary>
    Happy,
    /// <summary>Ocioso há muito tempo.</summary>
    Sleepy,
    /// <summary>Descansando (à noite, quando existir).</summary>
    Sleeping,
    /// <summary>Horda chegando, susto (sem gatilho ainda).</summary>
    Startled,
    /// <summary>Com fome ou trabalho parado (hoje: cabana cheia).</summary>
    Worried,
    /// <summary>Ferido ou aldeão próximo morreu (sem gatilho ainda).</summary>
    Crying,
    /// <summary>Interrompido várias vezes (sem gatilho ainda).</summary>
    Angry,
}
