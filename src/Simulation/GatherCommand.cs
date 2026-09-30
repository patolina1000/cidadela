namespace Cidadela.Simulation;

/// <summary>
/// Pede ao Castelão para coletar o recurso daquela célula (se houver e estiver no alcance). Gravando uma ladainha, vira
/// "colher [recurso] mais perto" (docs/ladainhas.md).
/// </summary>
public sealed record GatherCommand(GridPos Cell) : ISimCommand
{
    public void Apply(SimWorld world)
    {
        world.Castellan.StartGathering(world, Cell);
        // Ensinando: grava a intenção ("colher [recurso] mais perto" em volta daqui), não a árvore exata.
        string? kind = world.Castellan.GatherTarget?.Cell == Cell ? world.Castellan.GatherTarget.Kind
            : world.Castellan.DigCell == Cell ? world.Data.Castellan.Dig?.Item
            : null;
        if (kind is null)
            return;
        // Dentro da área de uma cabana do mesmo recurso (ou de um Posto de Carregadores), grava "perto da cabana".
        if (world.PlaceAround(Cell, kind) is Building place)
            world.Record(new LitanyCommand(LitanyVerb.Gather, new LitanyTarget(LitanyTargetKind.Resource, place.Cell, kind, 0f, Anchored: true)));
        else
            world.Record(new LitanyCommand(LitanyVerb.Gather,
                new LitanyTarget(LitanyTargetKind.Resource, Cell, kind, world.Data.Villagers.LitanyRadius)));
    }
}
