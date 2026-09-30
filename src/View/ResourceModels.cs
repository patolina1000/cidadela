using System;
using System.Collections.Generic;
using System.Text.Json;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Recursos do mapa com os modelos do CENÁRIO (assets/cenario/cenario.json): por célula, a variação é sorteada pelo
/// peso do manifesto e o giro (0–360°) e a escala (0,9–1,1) também, tudo fixo pela posição (a mesma célula sempre dá a
/// mesma árvore). Um MultiMesh por variação; cada recurso é uma instância, e a transformação dela encolhe e sacode na
/// coleta. Os materiais do GLB viram o Toon.gdshader pela cor do glTF, com a borda de luz fria nos materiais de
/// "coldRim" e o esmaecimento do que tapa a protagonista nas árvores (data/visual.json). Um material por combinação
/// (cor, borda, esmaecimento), compartilhado. Recurso sem entrada no manifesto: forma provisória (esfera).
/// </summary>
public partial class ResourceModels : Node3D
{
    private const string ManifestPath = "res://assets/cenario/cenario.json";
    private const float MinScale = 0.9f, MaxScale = 1.1f;

    private static readonly Dictionary<(Color, bool, bool), ShaderMaterial> Materials = new();

    /// <summary>Instância de um recurso: em qual MultiMesh, qual índice e a transformação sorteada.</summary>
    public sealed class Handle
    {
        public required MultiMesh Mesh { get; init; }
        public required int Index { get; init; }
        public required Vector3 Position { get; init; }
        public required float Yaw { get; init; }
        public required float Scale { get; init; }
        public required float Height { get; init; }
    }

    private readonly Dictionary<ResourceNode, Handle> _handles = new();

    public Handle this[ResourceNode resource] => _handles[resource];

    public void Build(IReadOnlyList<ResourceNode> resources, GameData data)
    {
        Dictionary<string, List<Variant>> manifest = LoadManifest();
        // Primeiro sorteia cada recurso; depois cria um MultiMesh por variação com o número certo de instâncias.
        var picks = new List<(ResourceNode Resource, Variant Variant, float Yaw, float Scale)>();
        var counts = new Dictionary<Variant, int>();
        foreach (ResourceNode resource in resources)
        {
            if (!manifest.TryGetValue(resource.Kind, out List<Variant>? variants) || variants.Count == 0)
                variants = new List<Variant> { Variant.Provisional(resource.Kind, data) };
            uint h = Hash(resource.Cell.X, resource.Cell.Z);
            Variant variant = Pick(variants, Unit(h));
            float yaw = Unit(Hash2(h, 1)) * Mathf.Tau;
            float scale = Mathf.Lerp(MinScale, MaxScale, Unit(Hash2(h, 2)));
            picks.Add((resource, variant, yaw, scale));
            counts[variant] = counts.GetValueOrDefault(variant) + 1;
        }

        var meshes = new Dictionary<Variant, MultiMesh>();
        var next = new Dictionary<Variant, int>();
        foreach ((Variant variant, int count) in counts)
        {
            var multimesh = new MultiMesh { TransformFormat = MultiMesh.TransformFormatEnum.Transform3D, Mesh = variant.Mesh, InstanceCount = count };
            AddChild(new MultiMeshInstance3D
            {
                Name = variant.Name,
                Multimesh = multimesh,
                CastShadow = variant.CastsShadow ? GeometryInstance3D.ShadowCastingSetting.On : GeometryInstance3D.ShadowCastingSetting.Off,
            });
            meshes[variant] = multimesh;
            next[variant] = 0;
        }

        foreach ((ResourceNode resource, Variant variant, float yaw, float scale) in picks)
        {
            var handle = new Handle
            {
                Mesh = meshes[variant], Index = next[variant]++, Yaw = yaw, Scale = scale, Height = variant.Height * scale,
                Position = new Vector3(resource.Cell.X + 0.5f, 0f, resource.Cell.Z + 0.5f),
            };
            _handles[resource] = handle;
            SetSize(handle, Vector3.One);
        }
    }

    /// <summary>Encolhe e sacode a instância (1 = tamanho sorteado); zero esconde.</summary>
    public static void SetSize(Handle handle, Vector3 size)
    {
        var basis = new Basis(Vector3.Up, handle.Yaw).Scaled(size * handle.Scale);
        handle.Mesh.SetInstanceTransform(handle.Index, new Transform3D(basis, handle.Position));
    }

    public static void Hide(Handle handle) =>
        handle.Mesh.SetInstanceTransform(handle.Index, new Transform3D(Basis.Identity.Scaled(Vector3.Zero), handle.Position));

    /// <summary>Põe o centro do esmaecimento (o peito da protagonista) em todos os materiais; null desliga.</summary>
    public static void SetOcclusionCenter(Vector3? center)
    {
        foreach (((Color, bool, bool Occlusion) key, ShaderMaterial material) in Materials)
        {
            if (!key.Occlusion)
                continue;
            material.SetShaderParameter("occlusion_enabled", center is not null);
            if (center is Vector3 c)
                material.SetShaderParameter("occlusion_center", c);
        }
    }

    private static ShaderMaterial MaterialFor(Color color, bool rim, bool occlusion)
    {
        if (Materials.TryGetValue((color, rim, occlusion), out ShaderMaterial? material))
            return material;
        material = new ShaderMaterial { Shader = GD.Load<Shader>(VillagerLooks.ToonShaderPath) };
        material.SetShaderParameter("albedo", color);
        if (rim)
            VisualSettings.Current.ApplyRim(material);
        if (occlusion)
            VisualSettings.Current.ApplyOcclusion(material);
        Materials[(color, rim, occlusion)] = material;
        return material;
    }

    // ---- Manifesto ------------------------------------------------------------------------------------------

    private sealed class Variant
    {
        public required string Name { get; init; }
        public required Mesh Mesh { get; init; }
        public required float Weight { get; init; }
        public required float Height { get; init; }
        public required bool CastsShadow { get; init; }

        /// <summary>Esfera achatada na cor do item, para recurso que o manifesto ainda não tem.</summary>
        public static Variant Provisional(string kind, GameData data)
        {
            var mesh = new SphereMesh { Radius = 0.4f, Height = 0.8f, RadialSegments = 12, Rings = 6 };
            mesh.Material = MaterialFor(Palette.ForItem(data, kind), rim: true, occlusion: false);
            return new Variant { Name = $"{kind}_provisorio", Mesh = mesh, Weight = 1f, Height = 0.4f, CastsShadow = true };
        }
    }

    private static readonly Dictionary<string, List<Variant>> Loaded = new();

    private static Dictionary<string, List<Variant>> LoadManifest()
    {
        if (Loaded.Count > 0 || !FileAccess.FileExists(ManifestPath))
            return Loaded;
        var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true, ReadCommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true };
        var file = JsonSerializer.Deserialize<Dictionary<string, FamilyFile>>(FileAccess.GetFileAsString(ManifestPath), options) ?? new();
        foreach ((string kind, FamilyFile family) in file)
        {
            var list = new List<Variant>();
            // As árvores esmaecem quando tapam a protagonista; pedra e veio são baixos.
            bool occlusion = kind == "wood";
            foreach (VariantFile v in family.Variants)
            {
                string path = "res://" + v.File;
                if (ResourceLoader.Load<PackedScene>(path) is not PackedScene scene)
                {
                    GD.PushWarning($"[cenário] não carregou {path}");
                    continue;
                }
                list.Add(new Variant
                {
                    Name = System.IO.Path.GetFileNameWithoutExtension(v.File), Mesh = ToonMesh(scene, v.ColdRim, occlusion),
                    Weight = v.Weight ?? 0f, Height = v.Height, CastsShadow = v.CastsShadow,
                });
            }
            Loaded[kind] = list;
        }
        return Loaded;
    }

    /// <summary>A malha do GLB com cada material trocado pelo toon da mesma cor (borda se o nome estiver em coldRim).</summary>
    private static Mesh ToonMesh(PackedScene scene, List<string> coldRim, bool occlusion)
    {
        Node root = scene.Instantiate();
        MeshInstance3D source = FindMesh(root) ?? throw new FormatException($"{scene.ResourcePath} sem malha.");
        var mesh = (Mesh)source.Mesh.Duplicate();
        for (int i = 0; i < mesh.GetSurfaceCount(); i++)
        {
            Material? original = source.GetActiveMaterial(i);
            string name = original?.ResourceName ?? "";
            Color color = original is BaseMaterial3D b ? b.AlbedoColor : Colors.Magenta;
            mesh.SurfaceSetMaterial(i, MaterialFor(color, coldRim.Contains(name), occlusion));
        }
        root.Free();
        return mesh;
    }

    private static MeshInstance3D? FindMesh(Node node)
    {
        if (node is MeshInstance3D mesh)
            return mesh;
        foreach (Node child in node.GetChildren())
            if (FindMesh(child) is MeshInstance3D found)
                return found;
        return null;
    }

    private sealed class FamilyFile
    {
        public List<VariantFile> Variants { get; set; } = new();
    }

    private sealed class VariantFile
    {
        public string File { get; set; } = "";
        public float? Weight { get; set; }
        public float Height { get; set; }
        public List<string> ColdRim { get; set; } = new();
        public bool CastsShadow { get; set; } = true;
    }

    // ---- Sorteio fixo pela posição ---------------------------------------------------------------------------

    private static Variant Pick(List<Variant> variants, float r)
    {
        float total = 0f;
        foreach (Variant v in variants)
            total += v.Weight;
        float acc = 0f;
        foreach (Variant v in variants)
        {
            acc += v.Weight / Math.Max(total, 1e-6f);
            if (r < acc)
                return v;
        }
        return variants[^1];
    }

    private static uint Hash(int x, int z) => Hash2((uint)x * 73856093u ^ (uint)z * 19349663u, 0);

    private static uint Hash2(uint h, uint salt)
    {
        h ^= salt * 0x9E3779B9u;
        h ^= h >> 16; h *= 0x7FEB352Du; h ^= h >> 15; h *= 0x846CA68Bu; h ^= h >> 16;
        return h;
    }

    private static float Unit(uint h) => (h & 0xFFFFFF) / (float)0x1000000;
}
