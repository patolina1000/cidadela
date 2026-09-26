using System;
using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Grama só visual (GDD, seção 17) com o asset "Stylized Grass Shader" da StayAtHomeDev (MIT, em
/// assets/grama_stylized): as duas malhas de tufo dele espalhadas com MultiMesh e o shader dele (degradê da
/// base à ponta + manchas de cor por uma textura de ruído no mundo).
/// A densidade vem do terreno (grassDensity em data/terrain.json), interpolada entre células para as
/// bordas não ficarem quadradas. O mapa é dividido em blocos de <see cref="ChunkCells"/>×<see cref="ChunkCells"/>
/// células, com um MultiMeshInstance3D por malha em cada bloco: blocos fora da tela não são desenhados e, quando
/// algo é construído, só o bloco daquela célula é refeito (sem os tufos das células ocupadas).
/// </summary>
public partial class GrassField : Node3D
{
    private const int ChunkCells = 8;
    private const int MaxTuftsPerCell = 120;
    private const string AssetDir = "res://assets/grama_stylized/";
    // Cópia do shader do asset com o empurrão da protagonista.
    private const string ShaderPath = "res://src/View/Grass.gdshader";
    private static readonly string[] MeshFiles = { "grass.glb", "grass2.glb" };

    // Grama baixa: a protagonista tem ~0,75 de altura; a grama fica em até ~20% dela (com as manchas), e itens
    // nas esteiras ficam acima (embaixo de esteira nem há grama). A malha do asset é reescalada para essa altura.
    private const float MinHeight = 0.08f;
    private const float MaxHeight = 0.13f;
    // Manchas de altura: um ruído largo deixa trechos mais altos e outros mais baixos.
    private const float ClumpMin = 0.75f;
    private const float ClumpMax = 1.2f;

    // Cores do shader do asset: ponta (color) e base (color2), nos roxos da grama do chão. O shader multiplica
    // o degradê pela mancha de ruído, o que escurece; por isso as duas são mais claras que o chão.
    private static readonly Color TipColor = new("C4B3D6");
    private static readonly Color BaseColor = new("6A5B7C");
    private const float NoiseScale = 12f; // tamanho das manchas de cor, em células

    private WorldGrid _grid = null!;
    private GameData _data = null!;
    private Func<GridPos, bool> _blocked = null!;
    private Mesh[] _meshes = null!;
    private float[] _meshHeights = null!;
    private ShaderMaterial _material = null!;
    private MultiMeshInstance3D[,,] _chunks = null!;
    private readonly HashSet<Vector2I> _dirty = new();
    private readonly FastNoiseLite _clumps = new() { Frequency = 0.35f, Seed = 7 };

    /// <summary>Quantos tufos estão desenhados agora (para medir desempenho).</summary>
    public int TuftCount { get; private set; }

    public void Build(WorldGrid grid, GameData data, Func<GridPos, bool> blocked)
    {
        _grid = grid;
        _data = data;
        _blocked = blocked;
        _meshes = Array.ConvertAll(MeshFiles, f => LoadMesh(AssetDir + f));
        _meshHeights = Array.ConvertAll(_meshes, m => Mathf.Max(m.GetAabb().Size.Y, 0.001f));
        ShaderMaterial material = _material = BuildMaterial();

        int cx = (grid.Width + ChunkCells - 1) / ChunkCells;
        int cz = (grid.Height + ChunkCells - 1) / ChunkCells;
        _chunks = new MultiMeshInstance3D[cx, cz, _meshes.Length];
        for (int x = 0; x < cx; x++)
        for (int z = 0; z < cz; z++)
        {
            for (int m = 0; m < _meshes.Length; m++)
            {
                var node = new MultiMeshInstance3D
                {
                    Name = $"Grass_{x}_{z}_{m}",
                    MaterialOverride = material,
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                };
                AddChild(node);
                _chunks[x, z, m] = node;
            }
            RebuildChunk(x, z);
        }
    }

    /// <summary>Onde está a protagonista: a grama em volta dela se inclina para longe. Chamado a cada quadro.</summary>
    public void SetPusher(Vector3 position) => _material.SetShaderParameter("pusher_pos", position);

    /// <summary>A célula mudou (construiu, desmontou, recurso esgotou): refaz o bloco dela no próximo frame.</summary>
    public void MarkDirty(GridPos cell) => _dirty.Add(new Vector2I(cell.X / ChunkCells, cell.Z / ChunkCells));

    public override void _Process(double delta)
    {
        foreach (Vector2I c in _dirty)
            RebuildChunk(c.X, c.Y);
        _dirty.Clear();
    }

    /// <summary>O .glb importa como cena; a malha do tufo é a do primeiro MeshInstance3D dela.</summary>
    private static Mesh LoadMesh(string path)
    {
        Node scene = GD.Load<PackedScene>(path).Instantiate();
        Mesh mesh = scene.FindChildren("*", nameof(MeshInstance3D)) is { Count: > 0 } found
            ? ((MeshInstance3D)found[0]).Mesh
            : throw new InvalidOperationException($"Sem malha em {path}");
        scene.Free();
        return mesh;
    }

    private static ShaderMaterial BuildMaterial()
    {
        var noise = new NoiseTexture2D
        {
            Seamless = true,
            Noise = new FastNoiseLite { Frequency = 0.01f, Seed = 3 },
        };
        var material = new ShaderMaterial { Shader = GD.Load<Shader>(ShaderPath) };
        material.SetShaderParameter("color", TipColor);
        material.SetShaderParameter("color2", BaseColor);
        material.SetShaderParameter("noise", noise);
        material.SetShaderParameter("noiseScale", NoiseScale);
        return material;
    }

    private void RebuildChunk(int cx, int cz)
    {
        var transforms = new List<Transform3D>[_meshes.Length];
        for (int m = 0; m < _meshes.Length; m++)
            transforms[m] = new List<Transform3D>();

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

                int m = rng.RandiRange(0, _meshes.Length - 1);
                float clump = Mathf.Lerp(ClumpMin, ClumpMax, _clumps.GetNoise2D(px, pz) * 0.5f + 0.5f);
                float scale = rng.RandfRange(MinHeight, MaxHeight) * clump / _meshHeights[m];
                var basis = new Basis(Vector3.Up, rng.Randf() * Mathf.Tau).Scaled(Vector3.One * scale);
                transforms[m].Add(new Transform3D(basis, new Vector3(px, 0f, pz)));
            }
        }

        for (int m = 0; m < _meshes.Length; m++)
        {
            var mm = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                Mesh = _meshes[m],
                InstanceCount = transforms[m].Count,
            };
            for (int i = 0; i < transforms[m].Count; i++)
                mm.SetInstanceTransform(i, transforms[m][i]);

            MultiMeshInstance3D node = _chunks[cx, cz, m];
            TuftCount += transforms[m].Count - (node.Multimesh?.InstanceCount ?? 0);
            node.Multimesh = mm;
        }
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
}
