using System.Collections.Generic;
using System.Text.Json;
using Godot;

namespace Cidadela.View;

/// <summary>Leitura de data/biography.json (categorias e entradas da enciclopédia).</summary>
public static class Biography
{
    public const string Path = "res://data/biography.json";
    // Os JSON de data/ têm comentários, que o Json do Godot não aceita.
    private static readonly JsonDocumentOptions JsonOptions = new() { CommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true };

    public sealed record Category(string Id, string Name, string EmptyText);

    public sealed record Entry(string Id, string Name, string CategoryId, string Description, string Story,
        string Model, IReadOnlyList<string> Animations, bool Discovered)
    {
        /// <summary>"castellan", "building", "item", "resource" ou "" (só texto).</summary>
        public string ModelKind => Model.Split(':')[0];
        /// <summary>O que vem depois dos dois-pontos (kind de buildings/items/resources), ou "".</summary>
        public string ModelArg => Model.Contains(':') ? Model[(Model.IndexOf(':') + 1)..] : "";
    }

    public static (List<Category> categories, List<Entry> entries) Load()
    {
        var categories = new List<Category>();
        var entries = new List<Entry>();
        if (!FileAccess.FileExists(Path))
        {
            GD.PushWarning($"Biografia: {Path} não encontrado.");
            return (categories, entries);
        }
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(Path), JsonOptions);
        foreach (JsonElement c in doc.RootElement.GetProperty("categorias").EnumerateArray())
            categories.Add(new Category(c.GetProperty("id").GetString() ?? "", c.GetProperty("nome").GetString() ?? "",
                c.TryGetProperty("vazio", out JsonElement empty) ? empty.GetString() ?? "" : "Nenhum registro."));
        foreach (JsonElement e in doc.RootElement.GetProperty("entradas").EnumerateArray())
        {
            var animations = new List<string>();
            if (e.TryGetProperty("animacoes", out JsonElement anims))
                foreach (JsonElement a in anims.EnumerateArray())
                    animations.Add(a.GetString() ?? "");
            entries.Add(new Entry(
                e.GetProperty("id").GetString() ?? "",
                e.GetProperty("nome").GetString() ?? "",
                e.GetProperty("categoria").GetString() ?? "",
                e.GetProperty("descricao").GetString() ?? "",
                e.GetProperty("historia").GetString() ?? "",
                e.TryGetProperty("modelo", out JsonElement m) ? m.GetString() ?? "" : "",
                animations,
                !e.TryGetProperty("descoberto", out JsonElement d) || d.GetBoolean()));
        }
        return (categories, entries);
    }
}
