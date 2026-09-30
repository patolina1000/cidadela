namespace Cidadela.Simulation;

/// <summary>
/// Uma cabana: o ofício (o recurso e o raio) e o estoque. Não dá ordem a ninguém (docs/ladainhas.md): é um lugar que a
/// ladainha pode citar.
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
