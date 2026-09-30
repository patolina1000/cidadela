namespace Cidadela.Simulation;

/// <summary>
/// Mariposa de cristal ("moth" em data/buildings.json; docs/linha_energia.md): pega um item leve da célula a
/// <paramref name="Reach"/> células atrás dela e põe na célula à mesma distância na frente, em <paramref name="Ticks"/>
/// ticks por item (na velocidade da fração de mana; sem mana, pousa). Nível 1: alcance 1.
/// </summary>
public sealed record MothType(int Ticks, int Reach);
