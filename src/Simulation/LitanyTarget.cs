namespace Cidadela.Simulation;

/// <summary>
/// Para onde um comando aponta: uma construção (pela célula em que está), um tipo de recurso (o mais perto de
/// <paramref name="Cell"/>, dentro de <paramref name="Radius"/> células) ou uma célula do chão (docs/ladainhas.md, Q3).
/// </summary>
public sealed record LitanyTarget(LitanyTargetKind Kind, GridPos Cell, string? Resource = null, float Radius = 0f);

public enum LitanyTargetKind
{
    Building,
    Resource,
    Cell,
}
