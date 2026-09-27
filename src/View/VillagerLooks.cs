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

    private const string LooksPath = "res://data/villager_looks.json";
    private const string HairDir = "res://assets/modelos/aldeao_cabelos/";

    internal static readonly JsonDocumentOptions JsonOptions = new() { CommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true };
    private static List<Hair>? _hairs;
    private static readonly Dictionary<string, PackedScene?> _scenes = new();
    private static readonly HashSet<string> _warned = new();

    /// <summary>Cabelo da variação 1..N; null se a variação não existe no JSON.</summary>
    public static Hair? HairFor(int variant)
    {
        List<Hair> hairs = Hairs();
        return variant >= 1 && variant <= hairs.Count ? hairs[variant - 1] : null;
    }

    /// <summary>Instancia a peça de cabelo <paramref name="model"/>; null (careca) se o arquivo não existe.</summary>
    public static Node3D? InstantiateHair(string model)
    {
        if (string.IsNullOrEmpty(model))
            return null;
        PackedScene? scene = Scene(HairDir + model + ".glb", $"cabelo \"{model}\"");
        return scene?.Instantiate<Node3D>();
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
