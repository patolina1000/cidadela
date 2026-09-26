using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>
/// Dados de balanceamento lidos dos JSON de data/. Recebe o texto, não o caminho,
/// para não depender do sistema de arquivos do Godot (res://).
/// </summary>
public sealed class GameData
{
    internal static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
    };

    public IReadOnlyDictionary<string, ResourceType> Resources { get; }
    public CastellanStats Castellan { get; }

    /// <summary>Construções na ordem do arquivo (a ordem da barra de construção).</summary>
    public IReadOnlyList<BuildingType> Buildings { get; }

    private readonly Dictionary<string, BuildingType> _buildingByKind;

    private GameData(IReadOnlyDictionary<string, ResourceType> resources, CastellanStats castellan,
        List<BuildingType> buildings)
    {
        Resources = resources;
        Castellan = castellan;
        Buildings = buildings;
        _buildingByKind = new Dictionary<string, BuildingType>();
        foreach (BuildingType b in buildings)
            _buildingByKind[b.Kind] = b;
    }

    public BuildingType Building(string kind) =>
        _buildingByKind.TryGetValue(kind, out BuildingType? type)
            ? type
            : throw new FormatException($"Construção desconhecida: \"{kind}\".");

    public ResourceType Resource(string kind) =>
        Resources.TryGetValue(kind, out ResourceType? type)
            ? type
            : throw new FormatException($"Recurso desconhecido: \"{kind}\".");

    public static GameData Parse(string resourcesJson, string castellanJson, string buildingsJson)
    {
        var raw = JsonSerializer.Deserialize<Dictionary<string, ResourceData>>(resourcesJson, JsonOptions)
            ?? throw new FormatException("resources.json vazio.");
        var resources = new Dictionary<string, ResourceType>();
        foreach ((string kind, ResourceData r) in raw)
        {
            if (r.GatherSeconds <= 0f || r.Amount <= 0)
                throw new FormatException($"Recurso \"{kind}\" precisa de gatherSeconds e amount positivos.");
            int ticks = Math.Max(1, (int)MathF.Round(r.GatherSeconds * SimClock.TicksPerSecond));
            resources[kind] = new ResourceType(kind, r.Name, ticks, r.Amount);
        }

        var c = JsonSerializer.Deserialize<CastellanData>(castellanJson, JsonOptions)
            ?? throw new FormatException("castellan.json vazio.");
        var stats = new CastellanStats(c.Speed, c.Reach, c.GatherReach, c.Radius);

        // Lido como lista de pares para manter a ordem do arquivo.
        using JsonDocument doc = JsonDocument.Parse(buildingsJson, new JsonDocumentOptions
        {
            CommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        });
        var buildings = new List<BuildingType>();
        foreach (JsonProperty prop in doc.RootElement.EnumerateObject())
        {
            BuildingData b = prop.Value.Deserialize<BuildingData>(JsonOptions)
                ?? throw new FormatException($"Construção \"{prop.Name}\" vazia.");
            foreach ((string item, int amount) in b.Cost)
            {
                if (!resources.ContainsKey(item) || amount <= 0)
                    throw new FormatException($"Custo inválido em \"{prop.Name}\": {item} × {amount}.");
            }
            if (b.BeltSpeed < 0f)
                throw new FormatException($"beltSpeed negativo em \"{prop.Name}\".");
            buildings.Add(new BuildingType(prop.Name, b.Name, b.Cost, b.Solid, b.BeltSpeed, b.Storage));
        }

        return new GameData(resources, stats, buildings);
    }

    private sealed class BuildingData
    {
        public string Name { get; set; } = "";
        public Dictionary<string, int> Cost { get; set; } = new();
        public bool Solid { get; set; } = true;
        public float BeltSpeed { get; set; }
        public bool Storage { get; set; }
    }

    private sealed class ResourceData
    {
        public string Name { get; set; } = "";
        public float GatherSeconds { get; set; }
        public int Amount { get; set; }
    }

    private sealed class CastellanData
    {
        public float Speed { get; set; } = 6f;
        public float Reach { get; set; } = 10f;
        public float GatherReach { get; set; } = 1f;
        public float Radius { get; set; } = 0.3f;
    }
}
