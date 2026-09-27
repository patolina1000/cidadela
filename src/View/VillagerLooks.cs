using System.Collections.Generic;
using System.Text.Json;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Peças de aparência do aldeão lidas de data/villager_looks.json (cabelos) e data/head_pieces.json
/// (chapéus). As cenas dos GLB ficam em cache: todos os aldeões instanciam da mesma PackedScene, e o corpo,
/// o rig e as animações são sempre os do corpo-base (nada de um corpo por cabelo).
/// </summary>
public static class VillagerLooks
{
    public sealed record Hair(string Name, string Model, string UnderHat);

    /// <summary>O que a peça de cabeça faz com o cabelo (campo "cobre" de data/head_pieces.json).</summary>
    public enum Coverage { None, Partial, Total }

    public sealed record HeadPiece(string Kind, string Name, Coverage Covers, string Model);

    private const string LooksPath = "res://data/villager_looks.json";
    private const string HairDir = "res://assets/modelos/aldeao_cabelos/";
    private const string FacesPath = "res://assets/texturas/aldeao/expressoes.png";
    private const string HeadPiecesPath = "res://data/head_pieces.json";
    private const string HatDir = "res://assets/modelos/aldeao_chapeus/";
    private const int FaceGrid = 3;

    /// <summary>Camada de render das peças de cabeça (cabelo, chapéu): o decal do rosto não as atinge.</summary>
    public const uint HeadPieceLayer = 1u << 1;

    private static Texture2D[]? _faces;

    internal static readonly JsonDocumentOptions JsonOptions = new() { CommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true };
    private static List<Hair>? _hairs;
    private static Dictionary<string, HeadPiece>? _pieces;
    private static string _workerPiece = "";
    private static readonly Dictionary<string, PackedScene?> _scenes = new();
    private static readonly HashSet<string> _warned = new();

    /// <summary>Cabelo da variação 1..N; null se a variação não existe no JSON.</summary>
    public static Hair? HairFor(int variant)
    {
        List<Hair> hairs = Hairs();
        return variant >= 1 && variant <= hairs.Count ? hairs[variant - 1] : null;
    }

    /// <summary>
    /// Textura de uma expressão: o atlas 3×3 é fatiado uma vez em 9 texturas (Decal não lê região de atlas).
    /// null se o atlas não existe.
    /// </summary>
    public static Texture2D? FaceTexture(Cidadela.Simulation.VillagerExpression expression)
    {
        if (_faces is null)
        {
            _faces = new Texture2D[FaceGrid * FaceGrid];
            if (!ResourceLoader.Exists(FacesPath))
            {
                GD.PushWarning($"Aldeão: atlas de expressões {FacesPath} não encontrado.");
                return null;
            }
            Image atlas = GD.Load<Texture2D>(FacesPath).GetImage();
            if (atlas.IsCompressed())
                atlas.Decompress();
            int cell = atlas.GetWidth() / FaceGrid;
            for (int i = 0; i < _faces.Length; i++)
            {
                Image face = atlas.GetRegion(new Rect2I(i % FaceGrid * cell, i / FaceGrid * cell, cell, cell));
                face.GenerateMipmaps();
                _faces[i] = ImageTexture.CreateFromImage(face);
            }
        }
        int index = (int)expression;
        return index >= 0 && index < _faces.Length ? _faces[index] : null;
    }

    /// <summary>Peça de cabeça que um aldeão com cabana veste; null se o JSON não define.</summary>
    public static HeadPiece? WorkerPiece()
    {
        Dictionary<string, HeadPiece> pieces = Pieces();
        return pieces.TryGetValue(_workerPiece, out HeadPiece? piece) ? piece : null;
    }

    /// <summary>
    /// Instancia a peça de cabeça: o GLB em <see cref="HatDir"/>, ou, sem modelo, uma forma provisória (cone
    /// de chapéu de palha) na cor dada. A peça já fica na camada das peças de cabeça.
    /// </summary>
    public static Node3D InstantiateHeadPiece(HeadPiece piece, Color color)
    {
        Node3D? node = null;
        if (!string.IsNullOrEmpty(piece.Model))
            node = Scene(HatDir + piece.Model + ".glb", $"chapéu \"{piece.Kind}\"")?.Instantiate<Node3D>();
        if (node is null)
        {
            // Provisório: aba larga e copa baixa, como um chapéu de palha. A origem é o encaixe "Chapéu".
            node = new Node3D();
            var material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.95f };
            node.AddChild(new MeshInstance3D
            {
                Name = "Brim",
                Mesh = new CylinderMesh { TopRadius = 0.11f, BottomRadius = 0.115f, Height = 0.008f, Material = material },
                Position = new Vector3(0f, 0.004f, 0f),
            });
            node.AddChild(new MeshInstance3D
            {
                Name = "Crown",
                Mesh = new CylinderMesh { TopRadius = 0.035f, BottomRadius = 0.062f, Height = 0.05f, Material = material },
                Position = new Vector3(0f, 0.033f, 0f),
            });
        }
        SetLayer(node, HeadPieceLayer);
        return node;
    }

    private static Dictionary<string, HeadPiece> Pieces()
    {
        if (_pieces is not null)
            return _pieces;
        _pieces = new Dictionary<string, HeadPiece>();
        if (!FileAccess.FileExists(HeadPiecesPath))
        {
            GD.PushWarning($"Aldeão: {HeadPiecesPath} não encontrado; sem chapéus.");
            return _pieces;
        }
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(HeadPiecesPath), JsonOptions);
        foreach (JsonElement p in doc.RootElement.GetProperty("pieces").EnumerateArray())
        {
            string kind = p.GetProperty("kind").GetString() ?? "";
            Coverage covers = (p.GetProperty("cobre").GetString() ?? "nenhum") switch
            {
                "parcial" => Coverage.Partial,
                "total" => Coverage.Total,
                "nenhum" => Coverage.None,
                string other => throw new System.FormatException($"head_pieces.json: cobre \"{other}\" inválido em \"{kind}\" (nenhum, parcial ou total)."),
            };
            _pieces[kind] = new HeadPiece(kind, p.GetProperty("name").GetString() ?? kind, covers,
                p.TryGetProperty("model", out JsonElement m) ? m.GetString() ?? "" : "");
        }
        _workerPiece = doc.RootElement.TryGetProperty("worker", out JsonElement w) ? w.GetString() ?? "" : "";
        return _pieces;
    }

    /// <summary>Instancia a peça de cabelo <paramref name="model"/>; null (careca) se o arquivo não existe.</summary>
    public static Node3D? InstantiateHair(string model)
    {
        if (string.IsNullOrEmpty(model))
            return null;
        PackedScene? scene = Scene(HairDir + model + ".glb", $"cabelo \"{model}\"");
        Node3D? piece = scene?.Instantiate<Node3D>();
        if (piece is not null)
            SetLayer(piece, HeadPieceLayer);
        return piece;
    }

    /// <summary>Põe todas as malhas de uma peça numa camada de render.</summary>
    public static void SetLayer(Node3D piece, uint layer)
    {
        if (piece is VisualInstance3D visual)
            visual.Layers = layer;
        foreach (Node child in piece.FindChildren("*", nameof(VisualInstance3D), recursive: true, owned: false))
            ((VisualInstance3D)child).Layers = layer;
    }

    private static List<Hair> Hairs()
    {
        if (_hairs is not null)
            return _hairs;
        _hairs = new List<Hair>();
        if (!FileAccess.FileExists(LooksPath))
        {
            GD.PushWarning($"Aldeão: {LooksPath} não encontrado; todos carecas.");
            return _hairs;
        }
        // System.Text.Json, como o GameData: os JSON de data/ têm comentários, que o Json do Godot não aceita.
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(LooksPath), JsonOptions);
        foreach (JsonElement h in doc.RootElement.GetProperty("hairs").EnumerateArray())
        {
            _hairs.Add(new Hair(h.GetProperty("name").GetString() ?? "", h.GetProperty("model").GetString() ?? "",
                h.TryGetProperty("underHat", out JsonElement under) ? under.GetString() ?? "" : ""));
        }
        return _hairs;
    }

    private static PackedScene? Scene(string path, string label)
    {
        if (_scenes.TryGetValue(path, out PackedScene? cached))
            return cached;
        PackedScene? scene = ResourceLoader.Exists(path) ? GD.Load<PackedScene>(path) : null;
        if (scene is null && _warned.Add(path))
            GD.PushWarning($"Aldeão: {label} sem modelo em {path}.");
        _scenes[path] = scene;
        return scene;
    }
}
