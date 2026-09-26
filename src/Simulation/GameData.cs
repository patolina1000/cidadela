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

    private GameData(IReadOnlyDictionary<string, ResourceType> resources, CastellanStats castellan)
    {
        Resources = resources;
        Castellan = castellan;
    }

    public ResourceType Resource(string kind) =>
        Resources.TryGetValue(kind, out ResourceType? type)
            ? type
            : throw new FormatException($"Recurso desconhecido: \"{kind}\".");

    public static GameData Parse(string resourcesJson, string castellanJson)
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
        var stats = new CastellanStats(c.Speed, c.Reach, c.Radius);

        return new GameData(resources, stats);
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
        public float Radius { get; set; } = 0.3f;
    }
}
