namespace Cidadela.Simulation;

/// <summary>
/// Tipo de terreno do chão natural, vindo de data/terrain.json (GDD, seção 17, "Piso e chão").
/// Index é a posição no arquivo: é o número guardado em cada célula e a camada da textura na cena.
/// </summary>
public sealed record TerrainType(string Kind, string Name, string Texture, int Index);
