namespace Cidadela.Simulation;

public sealed class WorldGrid
{
    public int Width { get; }
    public int Height { get; }

    // Índice do TerrainType de cada célula (0 = o primeiro de data/terrain.json).
    private readonly byte[] _terrain;

    public WorldGrid(int width, int height)
    {
        Width = width;
        Height = height;
        _terrain = new byte[width * height];
    }

    public bool InBounds(GridPos pos) => pos.X >= 0 && pos.Z >= 0 && pos.X < Width && pos.Z < Height;

    public int TerrainAt(GridPos pos) => _terrain[pos.Z * Width + pos.X];

    internal void SetTerrain(GridPos pos, int index) => _terrain[pos.Z * Width + pos.X] = (byte)index;
}
