namespace Cidadela.Simulation;

/// <summary>
/// Posto de Carregadores ("carriers" em data/buildings.json): quantas vagas e o raio, em células
/// a partir do posto, em que os carregadores buscam itens (baú, cabana ou saída de máquina) e entregam (máquina que os aceita).
/// </summary>
public sealed record CarrierType(int Count, float Radius);
