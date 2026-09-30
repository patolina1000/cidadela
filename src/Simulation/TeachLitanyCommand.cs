namespace Cidadela.Simulation;

/// <summary>Dá uma ladainha a um aldeão (ou null: ele para). Ele recusa a que não cabe na Inteligência dele.</summary>
public sealed record TeachLitanyCommand(int VillagerId, Litany? Litany) : ISimCommand
{
    public void Apply(SimWorld world)
    {
        foreach (Villager v in world.Villagers)
            if (v.Id == VillagerId)
                v.Learn(world, Litany);
    }
}
