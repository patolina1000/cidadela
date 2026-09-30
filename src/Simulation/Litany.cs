using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Uma ladainha: a lista de comandos que o aldeão repete sempre do início (Inteligência 1; docs/ladainhas.md).
/// </summary>
public sealed record Litany(string Name, IReadOnlyList<LitanyCommand> Commands)
{
    /// <summary>A Inteligência que os comandos pedem (o maior requisito entre eles).</summary>
    public int RequiredIntelligence
    {
        get
        {
            int max = 1;
            foreach (LitanyCommand c in Commands)
                max = System.Math.Max(max, c.RequiredIntelligence);
            return max;
        }
    }
}
