using System;
using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Grama só visual (GDD, seção 17): tufos low-poly gerados por código e espalhados com MultiMesh.
/// A densidade vem do terreno (grassDensity em data/terrain.json), interpolada entre células para as
/// bordas não ficarem quadradas. O mapa é dividido em blocos de <see cref="ChunkCells"/>×<see cref="ChunkCells"/>
/// células, um MultiMeshInstance3D por bloco: blocos fora da tela não são desenhados e, quando algo é
/// construído, só o bloco daquela célula é refeito (sem os tufos das células ocupadas).
/// </summary>
public partial class GrassField : Node3D
{
    private const int ChunkCells = 8;
    private const int MaxTuftsPerCell = 9;
    private const string ShaderPath = "res://src/View/Grass.gdshader";

    // Tufo baixo: a protagonista tem ~0,75 de altura, então a grama fica em 7% a 13% dela; itens nas esteiras
    // ficam acima de 0,1 (e embaixo de esteira nem há grama).
    private const float MinHeight = 0.05f;
    private const float MaxHeight = 0.1f;

    private WorldGrid _grid = null!;
    private GameData _data = null!;
    private Func<GridPos, bool> _blocked = null!;
    private Mesh _tuft = null!;
    private ShaderMaterial _material = null!;
    private MultiMeshInstance3D[,] _chunks = null!;
    private readonly HashSet<Vector2I> _dirty = new();

    /// <summary>Quantos tufos estão desenhados agora (para medir desempenho).</summary>
    public int TuftCount { get; private set; }

    public void Build(WorldGrid grid, GameData data, Func<GridPos, bool> blocked)
    {
        _grid = grid;
        _data = data;
        _blocked = blocked;
        _tuft = BuildTuftMesh();
        _material = new ShaderMaterial { Shader = GD.Load<Shader>(ShaderPath) };

        int cx = (grid.Width + ChunkCells - 1) / ChunkCells;
        int cz = (grid.Height + ChunkCells - 1) / ChunkCells;
        _chunks = new MultiMeshInstance3D[cx, cz];
        for (int x = 0; x < cx; x++)
        for (int z = 0; z < cz; z++)
        {
            var node = new MultiMeshInstance3D
            {
                Name = $"Grass_{x}_{z}",
                MaterialOverride = _material,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(node);
            _chunks[x, z] = node;
            RebuildChunk(x, z);
        }
    }

    /// <summary>A célula mudou (construiu, desmontou, recurso esgotou): refaz o bloco dela no próximo frame.</summary>
    public void MarkDirty(GridPos cell) => _dirty.Add(new Vector2I(cell.X / ChunkCells, cell.Z / ChunkCells));

    public override void _Process(double delta)
    {
        foreach (Vector2I c in _dirty)
            RebuildChunk(c.X, c.Y);
        _dirty.Clear();
    }

    private void RebuildChunk(int cx, int cz)
    {
        var transforms = new List<Transform3D>();
        var colors = new List<Color>();
        var customs = new List<Color>();

        for (int x = cx * ChunkCells; x < Math.Min((cx + 1) * ChunkCells, _grid.Width); x++)
        for (int z = cz * ChunkCells; z < Math.Min((cz + 1) * ChunkCells, _grid.Height); z++)
        {
            var cell = new GridPos(x, z);
            if (_blocked(cell))
                continue;

            // Semente fixa por célula: a grama volta igual quando o bloco é refeito.
            var rng = new RandomNumberGenerator { Seed = (ulong)(x * 73856093 ^ z * 19349663) };
            for (int i = 0; i < MaxTuftsPerCell; i++)
            {
                float px = x + rng.Randf(), pz = z + rng.Randf();
                if (rng.Randf() >= DensityAt(px, pz))
                    continue;

                float height = rng.RandfRange(MinHeight, MaxHeight);
                float width = rng.RandfRange(0.55f, 0.85f);
                var basis = new Basis(Vector3.Up, rng.Randf() * Mathf.Tau).Scaled(new Vector3(width, height, width));
                transforms.Add(new Transform3D(basis, new Vector3(px, 0f, pz)));
                colors.Add(PickColor(rng));
                customs.Add(new Color(rng.Randf(), 0f, 0f, 0f));
            }
        }

        var mm = new MultiMesh
        {
            TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
            UseColors = true,
            UseCustomData = true,
            Mesh = _tuft,
            InstanceCount = transforms.Count,
        };
        for (int i = 0; i < transforms.Count; i++)
        {
            mm.SetInstanceTransform(i, transforms[i]);
            mm.SetInstanceColor(i, colors[i]);
            mm.SetInstanceCustomData(i, customs[i]);
        }

        MultiMeshInstance3D node = _chunks[cx, cz];
        TuftCount += transforms.Count - (node.Multimesh?.InstanceCount ?? 0);
        node.Multimesh = mm;
    }

    /// <summary>
    /// Densidade no ponto, interpolada entre os centros das 4 células vizinhas: a grama rareia aos poucos na
    /// borda de um terreno em vez de parar numa linha reta.
    /// </summary>
    private float DensityAt(float px, float pz)
    {
        float fx = px - 0.5f, fz = pz - 0.5f;
        int x0 = Mathf.FloorToInt(fx), z0 = Mathf.FloorToInt(fz);
        float tx = fx - x0, tz = fz - z0;
        float d00 = CellDensity(x0, z0), d10 = CellDensity(x0 + 1, z0);
        float d01 = CellDensity(x0, z0 + 1), d11 = CellDensity(x0 + 1, z0 + 1);
        return Mathf.Lerp(Mathf.Lerp(d00, d10, tx), Mathf.Lerp(d01, d11, tx), tz);
    }

    private float CellDensity(int x, int z)
    {
        x = Math.Clamp(x, 0, _grid.Width - 1);
        z = Math.Clamp(z, 0, _grid.Height - 1);
        return _data.Terrains[_grid.TerrainAt(new GridPos(x, z))].GrassDensity;
    }

    /// <summary>Maioria grama morta e musgo acinzentado; de vez em quando líquen roxo. Leve variação de brilho.</summary>
    private static Color PickColor(RandomNumberGenerator rng)
    {
        float roll = rng.Randf();
        Color c = roll < 0.46f ? Palette.DeadGrass : roll < 0.92f ? Palette.GrayMoss : Palette.PurpleLichen;
        float shade = rng.RandfRange(0.9f, 1.1f);
        // Cor de instância chega crua ao shader (sem a conversão que as cores de material têm): passa para linear.
        return new Color(c.R * shade, c.G * shade, c.B * shade).SrgbToLinear();
    }

    /// <summary>
    /// Um tufo com 4 folhas finas e curvas em volta do centro, cada folha com 3 triângulos (base em quad e
    /// ponta em triângulo): 12 triângulos. Altura 1 (a escala da instância dá a altura real). UV.y vai de 0 na
    /// base a 1 na ponta, para o shader clarear a ponta e dobrar só o alto com o vento.
    /// </summary>
    private static Mesh BuildTuftMesh()
    {
        var st = new SurfaceTool();
        st.Begin(Mesh.PrimitiveType.Triangles);
        st.SetColor(Colors.White);

        const int blades = 4;
        for (int b = 0; b < blades; b++)
        {
            float angle = b * Mathf.Tau / blades + 0.4f * b;
            var outward = new Vector3(Mathf.Cos(angle), 0f, Mathf.Sin(angle));
            var side = new Vector3(-outward.Z, 0f, outward.X);
            float lean = 0.13f + 0.05f * (b % 2);   // o quanto a folha abre para fora (pouco: de cima não vira estrela)
            float halfWidth = 0.032f;

            // Base, meio (dobrando para fora) e ponta: a curva vem do meio sair pouco e a ponta sair mais.
            Vector3 root = outward * 0.02f;
            Vector3 mid = root + outward * lean * 0.25f + Vector3.Up * 0.6f;
            Vector3 tip = root + outward * lean + Vector3.Up * 1f;

            Vector3 a = root - side * halfWidth, c = root + side * halfWidth;
            Vector3 d = mid - side * halfWidth * 0.7f, e = mid + side * halfWidth * 0.7f;

            AddVertex(st, a, 0f); AddVertex(st, c, 0f); AddVertex(st, e, 0.55f);
            AddVertex(st, a, 0f); AddVertex(st, e, 0.55f); AddVertex(st, d, 0.55f);
            AddVertex(st, d, 0.55f); AddVertex(st, e, 0.55f); AddVertex(st, tip, 1f);
        }
        st.GenerateNormals();
        return st.Commit();
    }

    private static void AddVertex(SurfaceTool st, Vector3 position, float heightFactor)
    {
        st.SetUV(new Vector2(0f, heightFactor));
        st.AddVertex(position);
    }
}
