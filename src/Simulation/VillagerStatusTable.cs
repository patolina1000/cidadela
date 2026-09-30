using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>
/// Textos, ícones e quais estados são problema (data/villager_status.json). Todo <see cref="VillagerStatus"/> precisa
/// de uma entrada; o ícone é o nome de uma forma que a view desenha por código.
/// </summary>
public sealed class VillagerStatusTable
{
    public sealed record Entry(VillagerStatus Status, string Text, bool Problem, string Icon);

    private readonly Dictionary<VillagerStatus, Entry> _entries;

    private VillagerStatusTable(Dictionary<VillagerStatus, Entry> entries) => _entries = entries;

    public Entry this[VillagerStatus status] => _entries[status];

    public static VillagerStatusTable Parse(string json)
    {
        var file = JsonSerializer.Deserialize<Dictionary<string, EntryFile>>(json, GameData.JsonOptions)
            ?? throw new FormatException("villager_status.json vazio.");
        var entries = new Dictionary<VillagerStatus, Entry>();
        foreach (VillagerStatus status in VillagerStatuses.All)
        {
            string name = VillagerStatuses.Name(status);
            if (!file.TryGetValue(name, out EntryFile? e) || e is null)
                throw new FormatException($"villager_status.json sem o estado \"{name}\".");
            if (string.IsNullOrWhiteSpace(e.Text) || string.IsNullOrWhiteSpace(e.Icon))
                throw new FormatException($"villager_status.json: \"{name}\" precisa de \"text\" e \"icon\".");
            entries[status] = new Entry(status, e.Text, e.Problem, e.Icon);
        }
        return new VillagerStatusTable(entries);
    }

    private sealed class EntryFile
    {
        public string? Text { get; set; }
        public bool Problem { get; set; }
        public string? Icon { get; set; }
    }
}
