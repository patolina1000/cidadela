namespace Cidadela.Simulation;

/// <summary>
/// Torre de mana ("tower" em data/buildings.json; docs/linha_energia.md, regra 6). <paramref name="Wire"/>: até quantas
/// células (centro a centro) o fio liga outra torre; <paramref name="Area"/>: lado do quadrado de abastecimento em volta
/// dela (5 = 5×5), que liga à rede o que estiver dentro.
/// </summary>
public sealed record TowerType(float Wire, int Area);
