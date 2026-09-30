namespace Cidadela.Simulation;

/// <summary>
/// Estado do aldeão para o ícone sobre a cabeça (docs/ladainhas.md, "Estados visíveis"). Quais são "problema" (ícone
/// sempre à mostra) e os textos ficam em data/villager_status.json; os outros só aparecem no modo de informação (Alt).
/// </summary>
public enum VillagerStatus
{
    /// <summary>Descansando (a noite, quando existir, liga).</summary>
    Resting,
    /// <summary>Sem ladainha: parado, esperando que alguém o ensine.</summary>
    NoLitany,
    /// <summary>Rezando a ladainha: fazendo o comando atual.</summary>
    Chanting,
    /// <summary>A ladainha travou: o comando atual não dá (o motivo está em <see cref="Villager.Stuck"/>).</summary>
    Stuck,
}

public static class VillagerStatuses
{
    /// <summary>Nome do estado nos JSON.</summary>
    public static string Name(VillagerStatus status) => status switch
    {
        VillagerStatus.Resting => "descansando",
        VillagerStatus.NoLitany => "sem_ladainha",
        VillagerStatus.Chanting => "ladainha",
        _ => "travado",
    };

    public static readonly VillagerStatus[] All =
    {
        VillagerStatus.Resting, VillagerStatus.NoLitany, VillagerStatus.Chanting, VillagerStatus.Stuck,
    };
}
