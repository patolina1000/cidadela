namespace Cidadela.Simulation;

/// <summary>
/// Posto de Carregadores ("carriers" em data/buildings.json; docs/cadeia_flecha.md): quantas vagas e o raio, em células
/// a partir do posto, em que os carregadores buscam o bruto (baú ou cabana) e entregam (máquina que o aceita).
/// </summary>
public sealed record CarrierType(int Count, float Radius);
