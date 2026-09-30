namespace Cidadela.Simulation;

/// <summary>
/// Tipo de terreno do chão natural, vindo de data/terrain.json (GDD, seção 17, "Piso e chão").
/// Index é a posição no arquivo: é o número guardado em cada célula e a camada da textura na cena.
/// GrassDensity (0 a 1) diz quanto tufo de grama a cena espalha por cima; é só visual. Water: água (rio, lago): ninguém
/// passa e só se constrói o que precisa de água (a roda d'água). Color: cor lisa (hex) quando não há textura.
/// </summary>
public sealed record TerrainType(string Kind, string Name, string Texture, int Index, float GrassDensity = 0f,
    bool Water = false, string Color = "");
