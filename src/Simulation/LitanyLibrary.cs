using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>
/// Ladainhas nomeadas, vindas de data/ladainhas.json (docs/ladainhas.md, Q10). Cada comando é um objeto com "do" e os
/// alvos: { "do": "take", "item": "water_jar", "building": [2, 12] }, { "do": "gather", "resource": "wood",
/// "near": [5, 5], "radius": 8 }, { "do": "goto", "cell": [4, 4] }, { "do": "operate", "building": [7, 8] },
/// { "do": "wait", "seconds": 2 }. Sem "radius" no colher, vale o raio padrão (data/villagers.json).
/// </summary>
public sealed class LitanyLibrary
{
    private readonly Dictionary<string, Litany> _byName;

    public IReadOnlyDictionary<string, Litany> All => _byName;

    private LitanyLibrary(Dictionary<string, Litany> byName) => _byName = byName;

    public static readonly LitanyLibrary Empty = new(new Dictionary<string, Litany>());

    public Litany this[string name] => _byName.TryGetValue(name, out Litany? litany)
        ? litany
        : throw new FormatException($"Ladainha desconhecida: \"{name}\".");

    public static LitanyLibrary Parse(string json, GameData data)
    {
        var file = JsonSerializer.Deserialize<Dictionary<string, LitanyData>>(json, GameData.JsonOptions)
            ?? throw new FormatException("ladainhas.json vazio.");
        var byName = new Dictionary<string, Litany>();
        foreach ((string name, LitanyData l) in file)
        {
            var commands = new List<LitanyCommand>();
            for (int i = 0; i < l.Commands.Count; i++)
                commands.Add(ParseCommand(l.Commands[i], data, $"ladainha \"{name}\", comando {i + 1}"));
            if (commands.Count == 0)
                throw new FormatException($"Ladainha \"{name}\" sem comandos.");
            byName[name] = new Litany(name, commands);
        }
        return new LitanyLibrary(byName);
    }

    private static LitanyCommand ParseCommand(CommandData c, GameData data, string where)
    {
        string? item = c.Item;
        if (item is not null)
            data.Item(item); // item desconhecido: erro com o nome
        switch (c.Do)
        {
            case "goto":
                return new LitanyCommand(LitanyVerb.GoTo, PlaceOf(c, where, allowCell: true));
            case "take":
            case "put":
                if (item is null)
                    throw new FormatException($"{where}: \"{c.Do}\" precisa de \"item\".");
                return new LitanyCommand(c.Do == "take" ? LitanyVerb.Take : LitanyVerb.Put, PlaceOf(c, where, allowCell: false), item);
            case "gather":
                if (c.Resource is null || c.Near is not { Length: 2 })
                    throw new FormatException($"{where}: \"gather\" precisa de \"resource\" e \"near\": [x, z].");
                if (c.Resource != data.Castellan.Dig?.Item)
                    data.Resource(c.Resource); // recurso desconhecido: erro com o nome
                float radius = c.Radius ?? data.Villagers.LitanyRadius;
                if (radius <= 0f)
                    throw new FormatException($"{where}: \"radius\" precisa ser positivo.");
                return new LitanyCommand(LitanyVerb.Gather,
                    new LitanyTarget(LitanyTargetKind.Resource, new GridPos(c.Near[0], c.Near[1]), c.Resource, radius));
            case "operate":
                return new LitanyCommand(LitanyVerb.Operate, PlaceOf(c, where, allowCell: false));
            case "wait":
                if (c.Seconds is not float seconds || seconds <= 0f)
                    throw new FormatException($"{where}: \"wait\" precisa de \"seconds\" positivo.");
                return new LitanyCommand(LitanyVerb.Wait, Ticks: Math.Max(1, (int)MathF.Round(seconds * SimClock.TicksPerSecond)));
            default:
                throw new FormatException($"{where}: comando desconhecido \"{c.Do}\" (goto, take, put, gather, operate, wait).");
        }
    }

    private static LitanyTarget PlaceOf(CommandData c, string where, bool allowCell)
    {
        if (c.Building is { Length: 2 } b)
            return new LitanyTarget(LitanyTargetKind.Building, new GridPos(b[0], b[1]));
        if (allowCell && c.Cell is { Length: 2 } cell)
            return new LitanyTarget(LitanyTargetKind.Cell, new GridPos(cell[0], cell[1]));
        throw new FormatException($"{where}: \"{c.Do}\" precisa de \"building\": [x, z]" + (allowCell ? " ou \"cell\": [x, z]." : "."));
    }

    private sealed class LitanyData
    {
        public List<CommandData> Commands { get; set; } = new();
    }

    private sealed class CommandData
    {
        public string Do { get; set; } = "";
        public string? Item { get; set; }
        public string? Resource { get; set; }
        public int[]? Building { get; set; }
        public int[]? Cell { get; set; }
        public int[]? Near { get; set; }
        public float? Radius { get; set; }
        public float? Seconds { get; set; }
    }
}
