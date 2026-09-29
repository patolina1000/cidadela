using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>
/// Tabela expressão → (quadro dos olhos, quadro da boca), por nome de quadro, mais os quadros do piscar. Lê
/// o mesmo formato de data/villager_expressions.json e do rosto.json da arte (contrato v2):
/// {"expressoes": {nome: {"olhos": ..., "boca": ...}}, "piscar": {"meioFechado": ..., "fechado": ...}}.
/// Sem "piscar", valem "meio_fechado" e "fechado".
/// </summary>
public sealed class FaceTable
{
    public const string DefaultHalfClosedEyes = "meio_fechado";
    public const string DefaultClosedEyes = "fechado";

    /// <summary>Quadro dos olhos na primeira e na última fase do piscar.</summary>
    public string HalfClosedEyes { get; }
    /// <summary>Quadro dos olhos no meio do piscar.</summary>
    public string ClosedEyes { get; }

    private readonly Dictionary<VillagerExpression, (string Eyes, string Mouth)> _frames = new();

    private FaceTable(string halfClosedEyes, string closedEyes)
    {
        HalfClosedEyes = halfClosedEyes;
        ClosedEyes = closedEyes;
    }

    public (string Eyes, string Mouth) For(VillagerExpression expression) =>
        _frames.TryGetValue(expression, out (string, string) frames) ? frames : _frames[VillagerExpression.Distracted];

    /// <summary>Todas as 9 expressões do GDD precisam estar na tabela; falta é erro de dados.</summary>
    public static FaceTable Parse(string json)
    {
        using JsonDocument doc = JsonDocument.Parse(json, new JsonDocumentOptions
        {
            CommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        });
        JsonElement root = doc.RootElement;
        string half = DefaultHalfClosedEyes, closed = DefaultClosedEyes;
        if (root.TryGetProperty("piscar", out JsonElement blink))
        {
            if (blink.TryGetProperty("meioFechado", out JsonElement h) && h.GetString() is { Length: > 0 } hs)
                half = hs;
            if (blink.TryGetProperty("fechado", out JsonElement c) && c.GetString() is { Length: > 0 } cs)
                closed = cs;
        }
        var table = new FaceTable(half, closed);
        if (!root.TryGetProperty("expressoes", out JsonElement expressions))
            throw new FormatException("Tabela de expressões sem o campo \"expressoes\".");
        foreach (VillagerExpression expression in VillagerExpressions.All)
        {
            string name = VillagerExpressions.Name(expression);
            if (!expressions.TryGetProperty(name, out JsonElement entry))
                throw new FormatException($"Tabela de expressões sem a expressão \"{name}\".");
            string eyes = entry.GetProperty("olhos").GetString() ?? "";
            string mouth = entry.GetProperty("boca").GetString() ?? "";
            if (eyes.Length == 0 || mouth.Length == 0)
                throw new FormatException($"Expressão \"{name}\" precisa de \"olhos\" e \"boca\".");
            table._frames[expression] = (eyes, mouth);
        }
        return table;
    }
}
