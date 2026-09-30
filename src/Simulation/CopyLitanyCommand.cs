using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Copia a ladainha de um aldeão para outros, de graça (docs/ladainhas.md, "Copiar"; a protagonista "recita" para eles).
/// Cada um começa do primeiro comando; quem não tem Inteligência para ela recusa (o resultado fica em
/// <see cref="SimWorld.LastCopyResults"/>).
/// </summary>
public sealed record CopyLitanyCommand(int FromId, IReadOnlyList<int> ToIds) : ISimCommand
{
    public void Apply(SimWorld world) => world.CopyLitany(FromId, ToIds);
}
