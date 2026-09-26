namespace Cidadela.Simulation;

/// <summary>Estado de uma cabana de trabalho: o ofício, quem trabalha nela e o que já foi entregue.</summary>
public sealed class Workplace
{
    public JobType Job { get; }
    public Villager? Worker { get; internal set; }
    public Inventory Stored { get; } = new();

    public int Free => Job.Capacity - Stored.Count(Job.Resource);

    public Workplace(JobType job)
    {
        Job = job;
    }
}
