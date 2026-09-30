namespace Cidadela.Simulation;

/// <summary>
/// Definição de um recurso bruto, vinda de data/resources.json. <paramref name="TrunkRadius"/>: se tem, o nó bloqueia só um
/// círculo desse raio no centro da célula (o tronco da árvore) e a coleta conta até ele; sem, bloqueia a célula inteira.
/// </summary>
public sealed record ResourceType(string Kind, string Name, int GatherTicks, int StartAmount, float? TrunkRadius = null);
