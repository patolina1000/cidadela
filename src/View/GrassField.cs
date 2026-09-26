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
/// LOD: cada bloco existe em duas versões com os mesmos tufos nos mesmos lugares, a malha completa do asset
/// (perto) e uma simplificada gerada na carga (longe, a partir de <see cref="LodDistance"/> da câmera). A
/// câmera normal fica a 16 do chão, então no jogo quase sempre se vê a versão simplificada; a completa aparece
/// na cinematográfica e no zoom máximo. O nó de cada bloco fica no centro dele, porque o Godot mede a
/// distância do LOD à origem do nó.
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
    // A partir desta distância do centro do bloco a grama usa a malha simplificada (o tufo tem poucos pixels).
    private const float LodDistance = 11f;
    private const float LodMargin = 2f;

    private WorldGrid _grid = null!;
    private GameData _data = null!;
    private Func<GridPos, bool> _blocked = null!;
    private Mesh[] _meshes = null!;
    private Mesh[] _farMeshes = null!;
    private float[] _meshHeights = null!;
    private ShaderMaterial _material = null!;
    private MultiMeshInstance3D[,,] _chunks = null!;
    private MultiMeshInstance3D[,,] _farChunks = null!;
    private readonly HashSet<Vector2I> _dirty = new();
    private readonly FastNoiseLite _clumps = new() { Frequency = 0.35f, Seed = 7 };

    /// <summary>Quantos tufos estão desenhados agora (para medir desempenho).</summary>
    public int TuftCount { get; private set; }

    private bool _lodEnabled = true;

    /// <summary>Desliga o LOD (malha completa em qualquer distância) para comparar visual e custo.</summary>
    public bool LodEnabled
    {
        get => _lodEnabled;
        set
        {
            _lodEnabled = value;
            foreach (MultiMeshInstance3D near in _chunks)
            {
                near.VisibilityRangeEnd = value ? LodDistance : 0f;
                near.VisibilityRangeEndMargin = value ? LodMargin : 0f;
            }
            foreach (MultiMeshInstance3D far in _farChunks)
                far.Visible = value;
        }
    }

    public void Build(WorldGrid grid, GameData data, Func<GridPos, bool> blocked)
    {
        _grid = grid;
        _data = data;
        _blocked = blocked;
        _meshes = Array.ConvertAll(MeshFiles, f => LoadMesh(AssetDir + f));
        _farMeshes = Array.ConvertAll(_meshes, SimplifyMesh);
        _meshHeights = Array.ConvertAll(_meshes, m => Mathf.Max(m.GetAabb().Size.Y, 0.001f));
        ShaderMaterial material = _material = BuildMaterial();

        int cx = (grid.Width + ChunkCells - 1) / ChunkCells;
        int cz = (grid.Height + ChunkCells - 1) / ChunkCells;
        _chunks = new MultiMeshInstance3D[cx, cz, _meshes.Length];
        _farChunks = new MultiMeshInstance3D[cx, cz, _meshes.Length];
        for (int x = 0; x < cx; x++)
        for (int z = 0; z < cz; z++)
        {
            Vector3 center = ChunkCenter(x, z);
            for (int m = 0; m < _meshes.Length; m++)
            {
                _chunks[x, z, m] = AddChunkNode($"Grass_{x}_{z}_{m}", center, material, near: true);
                _farChunks[x, z, m] = AddChunkNode($"GrassFar_{x}_{z}_{m}", center, material, near: false);
            }
            RebuildChunk(x, z);
        }
        // Ligado por padrão; o painel de desempenho (F12) desliga para comparar.
        LodEnabled = true;
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

    private MultiMeshInstance3D AddChunkNode(string name, Vector3 center, Material material, bool near)
    {
        var node = new MultiMeshInstance3D
        {
            Name = name,
            Position = center,
            MaterialOverride = material,
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            VisibilityRangeFadeMode = GeometryInstance3D.VisibilityRangeFadeModeEnum.Self,
        };
        if (near)
        {
            node.VisibilityRangeEnd = LodDistance;
            node.VisibilityRangeEndMargin = LodMargin;
        }
        else
        {
            node.VisibilityRangeBegin = LodDistance;
            node.VisibilityRangeBeginMargin = LodMargin;
        }
        AddChild(node);
        return node;
    }

    private Vector3 ChunkCenter(int cx, int cz) => new(
        (cx * ChunkCells + Math.Min((cx + 1) * ChunkCells, _grid.Width)) / 2f, 0f,
        (cz * ChunkCells + Math.Min((cz + 1) * ChunkCells, _grid.Height)) / 2f);

    /// <summary>
    /// Versão simplificada da malha para longe: as mesmas folhas, nos mesmos lugares, com a mesma largura e
    /// altura, mas cada folha curva (uma tira de ~13 triângulos) vira 3 triângulos (base em quad + ponta).
    /// Vista de cima, a folha tem poucos pixels e a curva não aparece; de perto a malha completa continua.
    /// (Os simplificadores por colapso de arestas não servem: ou não mudam nada ou viram uma mancha.)
    /// Uma folha é um grupo de triângulos ligados por vértices acima da raiz (na raiz as folhas se encostam).
    /// </summary>
    private static Mesh SimplifyMesh(Mesh mesh)
    {
        var st = new SurfaceTool();
        st.CreateFrom(mesh, 0);
        st.Index();
        Godot.Collections.Array arrays = st.CommitToArrays();
        Vector3[] vertices = arrays[(int)Mesh.ArrayType.Vertex].AsVector3Array();
        int[] indices = arrays[(int)Mesh.ArrayType.Index].AsInt32Array();
        int triangles = indices.Length / 3;

        float minY = float.MaxValue, maxY = float.MinValue;
        foreach (Vector3 v in vertices) { minY = Mathf.Min(minY, v.Y); maxY = Mathf.Max(maxY, v.Y); }
        float rootY = minY + (maxY - minY) * 0.12f;

        // Union-find dos triângulos pelos vértices acima da raiz.
        int[] parent = new int[triangles];
        for (int t = 0; t < triangles; t++) parent[t] = t;
        int Find(int t) { while (parent[t] != t) t = parent[t] = parent[parent[t]]; return t; }
        var owner = new Dictionary<int, int>();
        for (int t = 0; t < triangles; t++)
        for (int k = 0; k < 3; k++)
        {
            int v = indices[t * 3 + k];
            if (vertices[v].Y <= rootY) continue;
            if (owner.TryGetValue(v, out int other)) parent[Find(t)] = Find(other);
            else owner[v] = t;
        }
        var blades = new Dictionary<int, HashSet<int>>();
        for (int t = 0; t < triangles; t++)
        {
            int root = Find(t);
            if (!blades.TryGetValue(root, out HashSet<int>? set)) blades[root] = set = new HashSet<int>();
            for (int k = 0; k < 3; k++) set.Add(indices[t * 3 + k]);
        }

        var kept = new List<int>();
        foreach (HashSet<int> blade in blades.Values)
        {
            var byHeight = new List<int>(blade);
            if (byHeight.Count < 5)
                continue; // folha pequena demais para simplificar: fica como está (abaixo)
            byHeight.Sort((a, b) => vertices[a].Y.CompareTo(vertices[b].Y));
            int r0 = byHeight[0], r1 = byHeight[1], tip = byHeight[^1];
            float midY = (vertices[r0].Y + vertices[tip].Y) * 0.5f;
            // Os dois vértices mais perto do meio da altura; m0 é o que fica do lado de r0, para a tira não torcer.
            var mids = byHeight.GetRange(2, byHeight.Count - 3);
            mids.Sort((a, b) => Mathf.Abs(vertices[a].Y - midY).CompareTo(Mathf.Abs(vertices[b].Y - midY)));
            int m0 = mids[0], m1 = mids[1];
            if (vertices[m0].DistanceSquaredTo(vertices[r0]) > vertices[m1].DistanceSquaredTo(vertices[r0]))
                (m0, m1) = (m1, m0);
            kept.AddRange(new[] { r0, r1, m1, r0, m1, m0, m0, m1, tip });
        }
        foreach (HashSet<int> blade in blades.Values)
        {
            if (blade.Count >= 5) continue;
            for (int t = 0; t < triangles; t++)
                if (blade.Contains(indices[t * 3]))
                    for (int k = 0; k < 3; k++) kept.Add(indices[t * 3 + k]);
        }
        if (kept.Count < 3 || blades.Count < 2)
            return mesh;

        arrays[(int)Mesh.ArrayType.Index] = kept.ToArray();
        var simplified = new ArrayMesh();
        simplified.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, arrays);
        GD.Print($"[grama] LOD: {blades.Count} folhas, {triangles} → {kept.Count / 3} triângulos");
        return simplified;
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
        Vector3 center = ChunkCenter(cx, cz);
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
                transforms[m].Add(new Transform3D(basis, new Vector3(px, 0f, pz) - center));
            }
        }

        for (int m = 0; m < _meshes.Length; m++)
        {
            MultiMeshInstance3D node = _chunks[cx, cz, m];
            TuftCount += transforms[m].Count - (node.Multimesh?.InstanceCount ?? 0);
            node.Multimesh = BuildMultiMesh(_meshes[m], transforms[m]);
            _farChunks[cx, cz, m].Multimesh = BuildMultiMesh(_farMeshes[m], transforms[m]);
        }
    }

    private static MultiMesh BuildMultiMesh(Mesh mesh, List<Transform3D> transforms)
    {
        var mm = new MultiMesh
        {
            TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
            Mesh = mesh,
            InstanceCount = transforms.Count,
        };
        for (int i = 0; i < transforms.Count; i++)
            mm.SetInstanceTransform(i, transforms[i]);
        return mm;
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
