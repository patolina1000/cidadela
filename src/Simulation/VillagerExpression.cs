namespace Cidadela.Simulation;

/// <summary>
/// Expressão do rosto do aldeão (GDD, tabela de expressões). Cada expressão vira um quadro de olhos e um de
/// boca pela tabela de data/villager_expressions.json (ou do rosto.json da arte, quando existir).
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

public static class VillagerExpressions
{
    /// <summary>Nome da expressão nos JSON (sem acento, como a arte grava no rosto.json).</summary>
    public static string Name(VillagerExpression expression) => expression switch
    {
        VillagerExpression.Distracted => "distraido",
        VillagerExpression.Effort => "esforco",
        VillagerExpression.Happy => "feliz",
        VillagerExpression.Sleepy => "sonolento",
        VillagerExpression.Sleeping => "dormindo",
        VillagerExpression.Startled => "espantado",
        VillagerExpression.Worried => "preocupado",
        VillagerExpression.Crying => "chorando",
        _ => "bravo",
    };

    public static readonly VillagerExpression[] All =
    {
        VillagerExpression.Distracted, VillagerExpression.Effort, VillagerExpression.Happy, VillagerExpression.Sleepy,
        VillagerExpression.Sleeping, VillagerExpression.Startled, VillagerExpression.Worried, VillagerExpression.Crying,
        VillagerExpression.Angry,
    };
}
