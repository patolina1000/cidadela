using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Definição de um recurso bruto, vinda de data/resources.json. <paramref name="Variants"/>: se tem, cada nó sorteia uma
/// (pelo peso, fixo pela célula) e bloqueia só o círculo dela no centro da célula, escalado pela escala sorteada entre
/// <paramref name="MinScale"/> e <paramref name="MaxScale"/>; a coleta conta até esse círculo. Sem variações, o nó
/// bloqueia a célula inteira.
/// </summary>
public sealed record ResourceType(string Kind, string Name, int GatherTicks, int StartAmount,
    IReadOnlyList<ResourceVariant> Variants, float MinScale = 1f, float MaxScale = 1f);
