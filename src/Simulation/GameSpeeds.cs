using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>Velocidades do tempo do jogo que o jogador pode escolher (data/time.json), da mais lenta à mais rápida.</summary>
public sealed class GameSpeeds
{
    public IReadOnlyList<int> Speeds { get; }

    private GameSpeeds(IReadOnlyList<int> speeds) => Speeds = speeds;

    public static GameSpeeds Parse(string json)
    {
        var file = JsonSerializer.Deserialize<TimeFile>(json, GameData.JsonOptions)
            ?? throw new FormatException("time.json vazio.");
        List<int> speeds = file.Speeds ?? throw new FormatException("time.json sem \"speeds\".");
        if (speeds.Count == 0)
            throw new FormatException("time.json: \"speeds\" precisa de pelo menos uma velocidade.");
        for (int i = 0; i < speeds.Count; i++)
        {
            if (speeds[i] < 1)
                throw new FormatException($"time.json: velocidade {speeds[i]} menor que 1.");
            if (i > 0 && speeds[i] <= speeds[i - 1])
                throw new FormatException("time.json: velocidades precisam estar em ordem crescente.");
        }
        return new GameSpeeds(speeds);
    }

    private sealed class TimeFile
    {
        public List<int>? Speeds { get; set; }
    }
}
