namespace Cidadela.Simulation;

public sealed class WorldGrid
{
    public int Width { get; }
    public int Height { get; }

    public WorldGrid(int width, int height)
    {
        Width = width;
        Height = height;
    }

    public bool InBounds(GridPos pos) => pos.X >= 0 && pos.Z >= 0 && pos.X < Width && pos.Z < Height;
}
