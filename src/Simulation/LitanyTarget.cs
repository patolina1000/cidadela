namespace Cidadela.Simulation;

/// <summary>
/// Para onde um comando aponta: uma construção (pela célula em que está), um tipo de recurso (o mais perto de
/// <paramref name="Cell"/>, dentro de <paramref name="Radius"/> células) ou uma célula do chão (docs/ladainhas.md, Q3).
/// <paramref name="Anchored"/>: o recurso é buscado na área de uma construção citada (a cabana ou o Posto de
/// Carregadores em <paramref name="Cell"/>; ajuste 2 do Arthur): o raio é o dela, e se ela sumir a ladainha trava.
/// </summary>
public sealed record LitanyTarget(LitanyTargetKind Kind, GridPos Cell, string? Resource = null, float Radius = 0f,
    bool Anchored = false);

public enum LitanyTargetKind
{
    Building,
    Resource,
    Cell,
}
