using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Definição de uma construção, vinda de data/buildings.json.
/// <paramref name="BeltSpeed"/> &gt; 0 = é esteira (células por segundo); <paramref name="Storage"/> = guarda itens;
/// <paramref name="Job"/> = cabana de trabalho; <paramref name="SpeedBonus"/> = multiplicador da velocidade de quem anda
/// sobre a construção (pisos construídos do GDD; 1 = nenhum); <paramref name="Posts"/> = postos que aldeões precisam
/// ocupar para ela andar (null = anda sozinha).
/// </summary>
public sealed record BuildingType(
    string Kind, string Name, IReadOnlyDictionary<string, int> Cost, bool Solid, float BeltSpeed = 0f, bool Storage = false,
    JobType? Job = null, float SpeedBonus = 1f, PostType? Posts = null)
{
    public bool IsBelt => BeltSpeed > 0f;
}
