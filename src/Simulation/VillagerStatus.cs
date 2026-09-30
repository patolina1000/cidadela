namespace Cidadela.Simulation;

/// <summary>
/// Estado do aldeão para o ícone sobre a cabeça. Quais são "problema" (ícone sempre à mostra) e os textos ficam em
/// data/villager_status.json; os outros só aparecem no modo de informação (Alt).
/// </summary>
public enum VillagerStatus
{
    /// <summary>Sem cabana: ninguém o chamou para trabalhar.</summary>
    Unemployed,
    /// <summary>A cabana encheu e ele não tem onde entregar.</summary>
    HutFull,
    /// <summary>Há recurso do ofício no raio, mas nenhum caminho até ele (ou até a cabana, para entregar).</summary>
    NoPath,
    /// <summary>Nenhum recurso do ofício dentro do raio da cabana.</summary>
    NoResource,
    /// <summary>Descansando (a noite, quando existir, liga).</summary>
    Resting,
    /// <summary>Coletando.</summary>
    Gathering,
    /// <summary>Voltando para a cabana com a carga.</summary>
    Carrying,
    /// <summary>Indo até o recurso.</summary>
    GoingToResource,
    /// <summary>Esperando o próximo passo (um instante entre uma tarefa e outra).</summary>
    Waiting,
}

public static class VillagerStatuses
{
    /// <summary>Nome do estado nos JSON.</summary>
    public static string Name(VillagerStatus status) => status switch
    {
        VillagerStatus.Unemployed => "sem_trabalho",
        VillagerStatus.HutFull => "cabana_cheia",
        VillagerStatus.NoPath => "sem_caminho",
        VillagerStatus.NoResource => "sem_recurso",
        VillagerStatus.Resting => "descansando",
        VillagerStatus.Gathering => "coletando",
        VillagerStatus.Carrying => "levando_carga",
        VillagerStatus.GoingToResource => "indo_ao_recurso",
        _ => "esperando",
    };

    public static readonly VillagerStatus[] All =
    {
        VillagerStatus.Unemployed, VillagerStatus.HutFull, VillagerStatus.NoPath, VillagerStatus.NoResource,
        VillagerStatus.Resting, VillagerStatus.Gathering, VillagerStatus.Carrying, VillagerStatus.GoingToResource,
        VillagerStatus.Waiting,
    };
}
