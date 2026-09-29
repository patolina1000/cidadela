using System.Collections.Generic;
using System.Text.Json;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Aparência do aldeão v2 (docs/aldeao_v2_contrato.md): lê data/villager_looks.json, data/head_pieces.json e o
/// rosto.json da arte; guarda em cache os GLB, as texturas do atlas e os materiais (toon da pele e do
/// cabelo, shader do rosto). Enquanto o corpo ou o rosto da arte não existem, entrega um atlas provisório
/// gerado por código (<see cref="FaceAtlasPlaceholder"/>) e o visual usa o placeholder.
/// </summary>
public static class VillagerLooks
{
    public const string LooksPath = "res://data/villager_looks.json";
    public const string HeadPiecesPath = "res://data/head_pieces.json";
    public const string ExpressionsPath = "res://data/villager_expressions.json";
    public const string ToonShaderPath = "res://src/View/Toon.gdshader";
    public const string FaceShaderPath = "res://src/View/VillagerFace.gdshader";
    private const string DefaultChestBone = "Spine";
    private const string DefaultHeadBone = "Head";

    internal static readonly JsonDocumentOptions JsonOptions = new() { CommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true };

    public sealed record Hair(string Name, string Model, string UnderHat);

    /// <summary>O que a peça de cabeça faz com o cabelo (campo "cobre" de data/head_pieces.json).</summary>
    public enum Coverage { None, Partial, Total }

    public sealed record HeadPiece(string Kind, string Name, Coverage Covers, string Model);

    /// <summary>Grade de um atlas do rosto: a célula inclui a margem; o retalho mostra a célula inteira.</summary>
    public sealed record FaceGrid(int Columns, int Rows, int CellWidth, int CellHeight, int Margin, IReadOnlyDictionary<string, int> Frames)
    {
        /// <summary>Largura ÷ altura da célula: a proporção do retalho é a mesma.</summary>
        public float Aspect => CellHeight > 0 ? (float)CellWidth / CellHeight : 1f;

        /// <summary>Índice do quadro pelo nome; -1 se não existe.</summary>
        public int Frame(string name) => Frames.TryGetValue(name, out int index) ? index : -1;
    }

    /// <summary>Tudo que o rosto.json diz (ou o provisório, quando ele não existe).</summary>
    public sealed record FaceInfo(FaceGrid Eyes, FaceGrid Mouth, FaceTable Table, string HeadBone, string ChestBone, float StrideRun, bool Provisional);

    private static bool _looksLoaded;
    private static string _bodyPath = "", _facePath = "", _hairDir = "";
    private static Color _skinColor = new("AEBFD3"), _hairColor = new("6F7F96");
    private static readonly List<Hair> _hairs = new();
    private static readonly List<Color> _hairTones = new();
    private static Dictionary<string, HeadPiece>? _pieces;
    private static string _workerPiece = "";
    private static FaceInfo? _face;
    private static Texture2D? _eyesAtlas, _mouthAtlas;
    private static ShaderMaterial? _skinMaterial, _hairMaterial, _eyesMaterial, _mouthMaterial;
    private static readonly Dictionary<string, PackedScene?> _scenes = new();
    private static readonly HashSet<string> _warned = new();

    public static Color SkinColor { get { LoadLooks(); return _skinColor; } }
    public static Color HairColor { get { LoadLooks(); return _hairColor; } }

    /// <summary>
    /// Tom do cabelo sorteado pelo id, independente do formato (outra mistura do id que a de
    /// <see cref="Villager.HairVariant"/>). Sem lista de tons, a cor base.
    /// </summary>
    public static Color HairToneFor(int seed)
    {
        LoadLooks();
        if (_hairTones.Count == 0)
            return _hairColor;
        return _hairTones[(int)(((uint)seed * 0x9E3779B1u) >> 8) % _hairTones.Count];
    }

    /// <summary>Aplica o tom a todas as malhas de uma peça de cabelo (parâmetro de instância do shader toon).</summary>
    public static void ApplyHairTone(Node3D hair, Color tone)
    {
        if (hair is MeshInstance3D single)
            single.SetInstanceShaderParameter("tint", tone);
        foreach (MeshInstance3D mesh in Descendants<MeshInstance3D>(hair))
            mesh.SetInstanceShaderParameter("tint", tone);
    }

    /// <summary>Cabelo da variação 1..N; null se a variação não existe no JSON.</summary>
    public static Hair? HairFor(int variant)
    {
        LoadLooks();
        return variant >= 1 && variant <= _hairs.Count ? _hairs[variant - 1] : null;
    }

    /// <summary>Se o corpo da arte existe; sem ele, o visual usa o placeholder.</summary>
    public static bool HasBodyModel
    {
        get { LoadLooks(); return ResourceLoader.Exists(_bodyPath); }
    }

    public static PackedScene? BodyScene()
    {
        LoadLooks();
        return Scene(_bodyPath, "corpo do aldeão");
    }

    /// <summary>Instancia uma peça de cabelo com o material toon do cabelo; null se o arquivo não existe.</summary>
    public static Node3D? InstantiateHair(string model)
    {
        LoadLooks();
        Node3D? node = Scene(_hairDir + model + ".glb", $"cabelo \"{model}\"")?.Instantiate<Node3D>();
        if (node is null)
            return null;
        foreach (MeshInstance3D mesh in Descendants<MeshInstance3D>(node))
            mesh.MaterialOverride = HairMaterial();
        ApplyHairTone(node, HairColor); // tom padrão; o visual troca pelo sorteado
        return node;
    }

    /// <summary>
    /// O cabelo pedido ou, se o arquivo dele não existe, o primeiro cabelo da lista que existir (aviso único).
    /// null só se nenhum existe.
    /// </summary>
    public static Node3D? InstantiateHairOrFallback(string model)
    {
        LoadLooks();
        if (ResourceLoader.Exists(_hairDir + model + ".glb"))
            return InstantiateHair(model);
        foreach (Hair hair in _hairs)
        {
            if (!ResourceLoader.Exists(_hairDir + hair.Model + ".glb"))
                continue;
            if (_warned.Add("fallback:" + model))
                GD.PushWarning($"Aldeão: cabelo \"{model}\" ainda não existe; usando \"{hair.Model}\" no lugar.");
            return InstantiateHair(hair.Model);
        }
        return null;
    }

    private static bool _speedChecked;

    /// <summary>
    /// Regra de velocidade (29/09/2026): velocidade ÷ passadaRun entre 1,0× e 1,5×. Fora disso, avisa uma vez
    /// com os números (o humano decide entre aldeão mais lento e passada mais longa); o visual prende a
    /// reprodução no limite e os pés deslizam o resto.
    /// </summary>
    public static void CheckSpeedRule(float cellsPerSecond)
    {
        if (_speedChecked)
            return;
        _speedChecked = true;
        float stride = Face().StrideRun;
        if (stride <= 0f)
            return;
        float ratio = cellsPerSecond / stride; // 1 célula = 1 m
        if (ratio < VillagerVisual.MinAnimationSpeed || ratio > VillagerVisual.MaxAnimationSpeed)
            GD.PushWarning($"Aldeão: velocidade {cellsPerSecond:0.###} m/s ÷ passadaRun {stride:0.###} m/s = {ratio:0.00}×, fora de 1,0×–1,5×. " +
                $"Ou a velocidade cai para {stride * VillagerVisual.MaxAnimationSpeed:0.###} m/s, ou a passada sobe para {cellsPerSecond / VillagerVisual.MaxAnimationSpeed:0.###} m/s ou mais.");
    }

    public static FaceInfo Face()
    {
        if (_face is not null)
            return _face;
        LoadLooks();
        if (FileAccess.FileExists(_facePath))
        {
            try
            {
                _face = ParseFace(FileAccess.GetFileAsString(_facePath));
                return _face;
            }
            catch (System.Exception e)
            {
                GD.PushError($"Aldeão: {_facePath} inválido ({e.Message}); usando o rosto provisório.");
            }
        }
        _face = ProvisionalFace();
        return _face;
    }

    /// <summary>Material toon da pele (compartilhado por todos os aldeões).</summary>
    public static ShaderMaterial SkinMaterial() => _skinMaterial ??= Toon(SkinColor);

    /// <summary>Material toon do cabelo: branco, a cor vem do "tint" por instância (<see cref="ApplyHairTone"/>).</summary>
    public static ShaderMaterial HairMaterial() => _hairMaterial ??= Toon(Colors.White);

    public static ShaderMaterial EyesMaterial() => _eyesMaterial ??= FaceMaterial(EyesAtlas(), Face().Eyes);

    public static ShaderMaterial MouthMaterial() => _mouthMaterial ??= FaceMaterial(MouthAtlas(), Face().Mouth);

    public static Texture2D EyesAtlas() => _eyesAtlas ??= Face().Provisional
        ? ImageTexture.CreateFromImage(FaceAtlasPlaceholder.EyesImage())
        : LoadAtlas("olhos.png");

    public static Texture2D MouthAtlas() => _mouthAtlas ??= Face().Provisional
        ? ImageTexture.CreateFromImage(FaceAtlasPlaceholder.MouthImage())
        : LoadAtlas("boca.png");

    /// <summary>Peça de cabeça que um aldeão com cabana veste; null se o JSON não define.</summary>
    public static HeadPiece? WorkerPiece()
    {
        Dictionary<string, HeadPiece> pieces = Pieces();
        return pieces.TryGetValue(_workerPiece, out HeadPiece? piece) ? piece : null;
    }

    /// <summary>
    /// Instancia a peça de cabeça no espaço do corpo (como os cabelos): o GLB, ou, sem modelo, uma forma
    /// provisória (chapéu de palha: aba larga e copa baixa) na cor dada, apoiada em <paramref name="headTop"/>.
    /// </summary>
    public static Node3D InstantiateHeadPiece(HeadPiece piece, Color color, Vector3 headTop)
    {
        LoadLooks();
        Node3D? node = null;
        if (!string.IsNullOrEmpty(piece.Model))
            node = Scene($"res://assets/modelos/aldeao_v2/chapeus/{piece.Model}.glb", $"chapéu \"{piece.Kind}\"")?.Instantiate<Node3D>();
        if (node is not null)
            return node;
        node = new Node3D();
        var material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.95f };
        node.AddChild(new MeshInstance3D
        {
            Mesh = new CylinderMesh { TopRadius = 0.11f, BottomRadius = 0.115f, Height = 0.012f, Material = material },
            Position = headTop + new Vector3(0f, -0.015f, 0f),
        });
        node.AddChild(new MeshInstance3D
        {
            Mesh = new CylinderMesh { TopRadius = 0.05f, BottomRadius = 0.06f, Height = 0.045f, Material = material },
            Position = headTop + new Vector3(0f, 0.012f, 0f),
        });
        return node;
    }

    public static IEnumerable<T> Descendants<T>(Node node) where T : Node
    {
        foreach (Node child in node.GetChildren())
        {
            if (child is T match)
                yield return match;
            foreach (T deeper in Descendants<T>(child))
                yield return deeper;
        }
    }

    // ---- leitura -------------------------------------------------------------------------------------------

    private static void LoadLooks()
    {
        if (_looksLoaded)
            return;
        _looksLoaded = true;
        if (!FileAccess.FileExists(LooksPath))
        {
            GD.PushWarning($"Aldeão: {LooksPath} não encontrado; sem cabelos e com as cores do contrato.");
            return;
        }
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(LooksPath), JsonOptions);
        JsonElement root = doc.RootElement;
        _bodyPath = root.TryGetProperty("corpo", out JsonElement body) ? body.GetString() ?? "" : "";
        _facePath = root.TryGetProperty("rosto", out JsonElement face) ? face.GetString() ?? "" : "";
        _hairDir = _bodyPath.Length > 0 ? _bodyPath[..(_bodyPath.LastIndexOf('/') + 1)] + "cabelos/" : "res://assets/modelos/aldeao_v2/cabelos/";
        if (root.TryGetProperty("corPele", out JsonElement skin))
            _skinColor = new Color(skin.GetString() ?? "AEBFD3");
        if (root.TryGetProperty("corCabelo", out JsonElement hair))
            _hairColor = new Color(hair.GetString() ?? "6F7F96");
        if (root.TryGetProperty("tonsCabelo", out JsonElement tones))
            foreach (JsonElement tone in tones.EnumerateArray())
                _hairTones.Add(new Color(tone.GetString() ?? "6F7F96"));
        if (root.TryGetProperty("cabelos", out JsonElement hairs))
            foreach (JsonElement h in hairs.EnumerateArray())
                _hairs.Add(new Hair(
                    h.GetProperty("name").GetString() ?? "",
                    h.GetProperty("model").GetString() ?? "",
                    h.TryGetProperty("underHat", out JsonElement under) ? under.GetString() ?? "" : ""));
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
                p.TryGetProperty("model", out JsonElement model) ? model.GetString() ?? "" : "");
        }
        _workerPiece = doc.RootElement.TryGetProperty("worker", out JsonElement worker) ? worker.GetString() ?? "" : "";
        return _pieces;
    }

    /// <summary>rosto.json do contrato: grades dos olhos e da boca, expressões, ossos e passada do run.</summary>
    private static FaceInfo ParseFace(string json)
    {
        using JsonDocument doc = JsonDocument.Parse(json, JsonOptions);
        JsonElement root = doc.RootElement;
        FaceGrid eyes = ParseGrid(root.GetProperty("olhos"), "olhos");
        FaceGrid mouth = ParseGrid(root.GetProperty("boca"), "boca");
        // As expressões da arte valem no lugar da tabela provisória de data/.
        FaceTable table = root.TryGetProperty("expressoes", out _) ? FaceTable.Parse(json) : FaceTable.Parse(FileAccess.GetFileAsString(ExpressionsPath));
        string head = root.TryGetProperty("ossoCabeca", out JsonElement h) ? h.GetString() ?? DefaultHeadBone : DefaultHeadBone;
        string chest = root.TryGetProperty("ossoPeito", out JsonElement c) ? c.GetString() ?? DefaultChestBone : DefaultChestBone;
        // Contrato de 29/09/2026: "passadaRun" (a passada do único clipe de movimento); "passadaWalk" era a versão anterior.
        float stride = root.TryGetProperty("passadaRun", out JsonElement s) ? s.GetSingle()
            : root.TryGetProperty("passadaWalk", out JsonElement w) ? w.GetSingle() : 0f;
        return new FaceInfo(eyes, mouth, table, head, chest, stride, Provisional: false);
    }

    private static FaceGrid ParseGrid(JsonElement grid, string name)
    {
        int columns = grid.GetProperty("colunas").GetInt32();
        int rows = grid.GetProperty("linhas").GetInt32();
        JsonElement cell = grid.GetProperty("celulaPx");
        int margin = grid.TryGetProperty("margemPx", out JsonElement m) ? m.GetInt32() : 0;
        if (columns <= 0 || rows <= 0)
            throw new System.FormatException($"rosto.json: \"{name}\" precisa de colunas e linhas positivas.");
        if (margin < 8)
            GD.PushWarning($"Aldeão: rosto.json: margemPx de \"{name}\" é {margin}; o contrato pede ao menos 8.");
        var frames = new Dictionary<string, int>();
        foreach (JsonProperty frame in grid.GetProperty("quadros").EnumerateObject())
            frames[frame.Name] = frame.Value.GetInt32();
        return new FaceGrid(columns, rows, cell[0].GetInt32(), cell[1].GetInt32(), margin, frames);
    }

    private static FaceInfo ProvisionalFace()
    {
        FaceTable table = FaceTable.Parse(FileAccess.GetFileAsString(ExpressionsPath));
        var eyes = new FaceGrid(FaceAtlasPlaceholder.EyesColumns, FaceAtlasPlaceholder.EyesRows, FaceAtlasPlaceholder.EyesCellWidth,
            FaceAtlasPlaceholder.EyesCellHeight, FaceAtlasPlaceholder.Margin, FaceAtlasPlaceholder.Frames(FaceAtlasPlaceholder.EyesFrames));
        var mouth = new FaceGrid(FaceAtlasPlaceholder.MouthColumns, FaceAtlasPlaceholder.MouthRows, FaceAtlasPlaceholder.MouthCellWidth,
            FaceAtlasPlaceholder.MouthCellHeight, FaceAtlasPlaceholder.Margin, FaceAtlasPlaceholder.Frames(FaceAtlasPlaceholder.MouthFrames));
        return new FaceInfo(eyes, mouth, table, DefaultHeadBone, DefaultChestBone, 0f, Provisional: true);
    }

    private static Texture2D LoadAtlas(string file)
    {
        string path = _facePath[..(_facePath.LastIndexOf('/') + 1)] + file;
        if (ResourceLoader.Exists(path))
            return GD.Load<Texture2D>(path);
        GD.PushWarning($"Aldeão: atlas {path} não encontrado; usando o provisório.");
        return ImageTexture.CreateFromImage(file == "olhos.png" ? FaceAtlasPlaceholder.EyesImage() : FaceAtlasPlaceholder.MouthImage());
    }

    private static ShaderMaterial Toon(Color color)
    {
        var material = new ShaderMaterial { Shader = GD.Load<Shader>(ToonShaderPath) };
        material.SetShaderParameter("albedo", color);
        return material;
    }

    private static ShaderMaterial FaceMaterial(Texture2D atlas, FaceGrid grid)
    {
        var material = new ShaderMaterial { Shader = GD.Load<Shader>(FaceShaderPath) };
        material.SetShaderParameter("atlas", atlas);
        material.SetShaderParameter("columns", grid.Columns);
        material.SetShaderParameter("rows", grid.Rows);
        return material;
    }

    private static PackedScene? Scene(string path, string what)
    {
        if (_scenes.TryGetValue(path, out PackedScene? cached))
            return cached;
        PackedScene? scene = ResourceLoader.Exists(path) ? GD.Load<PackedScene>(path) : null;
        if (scene is null && _warned.Add(path))
            GD.PushWarning($"Aldeão: {what} não encontrado em {path}.");
        _scenes[path] = scene;
        return scene;
    }
}
