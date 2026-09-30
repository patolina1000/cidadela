using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Uma rede de mana (docs/linha_energia.md, regra 6): torres ligadas pelo fio e o que está nas áreas delas. Grafo com
/// somas: as ligações só mudam quando uma construção entra ou sai; a cada tick só se somam geração e consumo. Faltou mana,
/// todos os consumidores recebem a mesma fração (<see cref="Satisfaction"/>) e ficam mais lentos por igual.
/// </summary>
public sealed class ManaNetwork
{
    public List<Building> Towers { get; } = new();

    /// <summary>Tudo o que está ligado: torres, geradores, consumidores e reservatórios.</summary>
    public List<Building> Members { get; } = new();

    /// <summary>Mana por segundo gerada neste tick.</summary>
    public float Supply { get; internal set; }

    /// <summary>Mana por segundo pedida pelos consumidores neste tick (sem contar o que vai para reservatórios).</summary>
    public float Demand { get; internal set; }

    /// <summary>Fração do pedido que os consumidores recebem: 1 com sobra; 0 sem geração.</summary>
    public float Satisfaction => Demand <= 0f ? (Supply > 0f ? 1f : 0f) : System.MathF.Min(1f, Supply / Demand);

    /// <summary>Mana por segundo que sobra depois dos consumidores (vai para os reservatórios, como o Cristal-mãe).</summary>
    public float Surplus => System.MathF.Max(0f, Supply - Demand);
}
