using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Definição de uma construção, vinda de data/buildings.json.
/// <paramref name="BeltSpeed"/> &gt; 0 = é esteira (células por segundo); <paramref name="Storage"/> = guarda itens;
/// <paramref name="Job"/> = cabana de trabalho; <paramref name="SpeedBonus"/> = multiplicador da velocidade de quem anda
/// sobre a construção (pisos construídos do GDD; 1 = nenhum); <paramref name="Posts"/> = postos que aldeões precisam
/// ocupar para ela andar (null = anda sozinha); <paramref name="Carriers"/> = vagas de carregador (Posto de Carregadores);
/// <paramref name="Hotbar"/> = aparece na barra de construção (falso: o código fica, mas o jogador não constrói);
/// <paramref name="Tower"/> = torre de mana; <paramref name="Mana"/> = gasta, gera ou guarda mana;
/// <paramref name="OnResource"/> = só se constrói sobre esse recurso e tira dele 1 a cada ciclo (a mina sobre o veio);
/// <paramref name="NextToWater"/> = só se constrói encostada (de lado) na água (o poço); <paramref name="Fixed"/> = já vem
/// no mapa e não se desmonta (o Cristal-mãe); <paramref name="Moth"/> = mariposa (leva itens leves de trás para a frente);
/// <paramref name="OnBank"/> = só se constrói na margem (o Barreiro); <paramref name="SpawnsVillager"/> = cada ciclo da
/// receita forma um aldeão (o Cristal-mãe).
/// </summary>
public sealed record BuildingType(
    string Kind, string Name, IReadOnlyDictionary<string, int> Cost, bool Solid, float BeltSpeed = 0f, bool Storage = false,
    JobType? Job = null, float SpeedBonus = 1f, PostType? Posts = null, CarrierType? Carriers = null,
    bool Hotbar = true, TowerType? Tower = null, ManaType? Mana = null, string? OnResource = null, bool NextToWater = false,
    bool Fixed = false, MothType? Moth = null, bool OnBank = false, bool SpawnsVillager = false)
{
    public bool IsBelt => BeltSpeed > 0f;
}
