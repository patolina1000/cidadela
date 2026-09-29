using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>
/// Tabela expressão → (quadro dos olhos, quadro da boca), por nome de quadro. Lê o mesmo formato de
/// data/villager_expressions.json e do rosto.json da arte (contrato v2, campo "expressoes"): um objeto
/// {"expressoes": {nome: {"olhos": ..., "boca": ...}}}. O quadro dos olhos fechados (piscar) vem de
/// "olhosFechados"; sem ele, vale "fechado".
/// </summary>
public sealed class FaceTable
{
    public const string DefaultClosedEyes = "fechado";

    /// <summary>Quadro dos olhos usado ao piscar.</summary>
    public string ClosedEyes { get; }

    private readonly Dictionary<VillagerExpression, (string Eyes, string Mouth)> _frames = new();

    private FaceTable(string closedEyes)
    {
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
        string closed = root.TryGetProperty("olhosFechados", out JsonElement c) ? c.GetString() ?? DefaultClosedEyes : DefaultClosedEyes;
        var table = new FaceTable(closed);
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
