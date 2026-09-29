namespace Cidadela.Simulation;

/// <summary>
/// Estado de uma cabana de trabalho: o ofício e o que já foi entregue.
/// Aguardando o novo aldeão: o trabalhador (quem coleta e entrega aqui) volta com ele.
/// </summary>
public sealed class Workplace
{
    public JobType Job { get; }
    public Inventory Stored { get; } = new();

    public int Free => Job.Capacity - Stored.Count(Job.Resource);

    public Workplace(JobType job)
    {
        Job = job;
    }
}
