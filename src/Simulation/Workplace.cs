namespace Cidadela.Simulation;

/// <summary>
/// Uma cabana: o ofício (o recurso e o raio) e o estoque. Não dá ordem a ninguém (docs/ladainhas.md): é um lugar que a
/// ladainha pode citar.
/// </summary>
public sealed class Workplace
{
    public JobType Job { get; }
    public Inventory Stored { get; } = new();

    /// <summary>Quanto ainda cabe no estoque (qualquer item conta).</summary>
    public int Free
    {
        get
        {
            int total = 0;
            foreach (int n in Stored.Counts.Values)
                total += n;
            return Job.Capacity - total;
        }
    }

    public Workplace(JobType job)
    {
        Job = job;
    }
}
