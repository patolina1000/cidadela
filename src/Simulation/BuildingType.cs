using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Definição de uma construção, vinda de data/buildings.json.
/// <paramref name="BeltSpeed"/> &gt; 0 = é esteira (células por segundo); <paramref name="Storage"/> = guarda itens;
/// <paramref name="Job"/> = cabana de trabalho; <paramref name="SpeedBonus"/> = multiplicador da velocidade de quem anda
/// sobre a construção (pisos construídos do GDD; 1 = nenhum); <paramref name="Posts"/> = postos que aldeões precisam
/// ocupar para ela andar (null = anda sozinha); <paramref name="Carriers"/> = vagas de carregador (Posto de Carregadores);
/// <paramref name="Torque"/> = parte de uma rede de torque; <paramref name="NeedsWater"/> = só se constrói na água (roda);
/// <paramref name="Powered"/> = esteira que só anda com manivela ou eixo (era do torque);
/// <paramref name="CrankCells"/> &gt; 0 = manivela: quantas células de esteira ela move.
/// </summary>
public sealed record BuildingType(
    string Kind, string Name, IReadOnlyDictionary<string, int> Cost, bool Solid, float BeltSpeed = 0f, bool Storage = false,
    JobType? Job = null, float SpeedBonus = 1f, PostType? Posts = null, CarrierType? Carriers = null,
    TorqueType? Torque = null, bool NeedsWater = false, bool Powered = false, int CrankCells = 0)
{
    public bool IsBelt => BeltSpeed > 0f;
    public bool IsCrank => CrankCells > 0;
}
