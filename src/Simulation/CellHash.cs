namespace Cidadela.Simulation;

/// <summary>
/// Sorteio fixo pela posição: a mesma célula sempre dá o mesmo número. A simulação usa para a variação e a escala dos
/// recursos; a cena, para o giro (que não muda o jogo).
/// </summary>
public static class CellHash
{
    public static uint Of(int x, int z) => Mix((uint)x * 73856093u ^ (uint)z * 19349663u, 0);

    public static uint Mix(uint h, uint salt)
    {
        h ^= salt * 0x9E3779B9u;
        h ^= h >> 16; h *= 0x7FEB352Du; h ^= h >> 15; h *= 0x846CA68Bu; h ^= h >> 16;
        return h;
    }

    /// <summary>Número de 0 (incluso) a 1 (excluso).</summary>
    public static float Unit(uint h) => (h & 0xFFFFFF) / (float)0x1000000;
}
