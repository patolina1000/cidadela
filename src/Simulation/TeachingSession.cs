using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Ensinar por demonstração (docs/ladainhas.md): enquanto grava, o que a protagonista faz vira comando, gravando a
/// intenção e não a coordenada (colher = "colher [recurso] mais perto" em volta de onde ela colheu). "Ir até" só quando
/// ela marca uma célula (Q11). Comandos repetidos seguidos (pôr o mesmo item várias vezes, colher o mesmo recurso) viram um.
/// </summary>
public sealed class TeachingSession
{
    public Villager Villager { get; }
    public List<LitanyCommand> Commands { get; } = new();

    public TeachingSession(Villager villager) => Villager = villager;

    internal void Record(LitanyCommand command)
    {
        if (Commands.Count > 0 && SameIntent(Commands[^1], command))
            return;
        Commands.Add(command);
    }

    private static bool SameIntent(LitanyCommand a, LitanyCommand b) =>
        a.Verb == b.Verb && a.Item == b.Item && a.Target?.Kind == b.Target?.Kind &&
        (a.Verb == LitanyVerb.Gather ? a.Target!.Resource == b.Target!.Resource : a.Target?.Cell == b.Target?.Cell);
}
