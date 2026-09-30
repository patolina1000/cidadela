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
    /// <summary>Chamado para o posto de uma máquina, indo até ela.</summary>
    GoingToPost,
    /// <summary>No posto, encostado na máquina.</summary>
    AtPost,
    /// <summary>Carregador indo buscar bruto.</summary>
    Fetching,
    /// <summary>Carregador levando bruto para a máquina.</summary>
    Hauling,
    /// <summary>Carregador sem o que levar: nenhuma máquina no raio pede bruto que exista num baú ou cabana.</summary>
    NothingToHaul,
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
        VillagerStatus.GoingToPost => "indo_ao_posto",
        VillagerStatus.AtPost => "no_posto",
        VillagerStatus.Fetching => "buscando_carga",
        VillagerStatus.Hauling => "levando_para_maquina",
        VillagerStatus.NothingToHaul => "sem_o_que_carregar",
        _ => "esperando",
    };

    public static readonly VillagerStatus[] All =
    {
        VillagerStatus.Unemployed, VillagerStatus.HutFull, VillagerStatus.NoPath, VillagerStatus.NoResource,
        VillagerStatus.Resting, VillagerStatus.Gathering, VillagerStatus.Carrying, VillagerStatus.GoingToResource,
        VillagerStatus.Waiting, VillagerStatus.GoingToPost, VillagerStatus.AtPost,
        VillagerStatus.Fetching, VillagerStatus.Hauling, VillagerStatus.NothingToHaul,
    };
}
