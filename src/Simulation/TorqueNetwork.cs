using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Uma rede de torque: construções com torque ligadas por vizinhança (grafo com somas, sem simular peça por peça). Gira
/// se a força das rodas cobre a demanda dos consumidores; sobrecarregada ou sem roda, a rede inteira para.
/// </summary>
public sealed class TorqueNetwork
{
    public List<Building> Members { get; } = new();
    public float Supply { get; internal set; }
    public float Demand { get; internal set; }
    public bool Turning => Supply > 0f && Supply >= Demand;
}
