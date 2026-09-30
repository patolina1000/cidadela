using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Palavras do jogo para as ladainhas (docs/ladainhas.md): cada comando como frase curta, a cor do bloco por tipo de
/// comando (estilo Scratch) e o motivo de uma trava ("nunca travar calado").
/// </summary>
public static class LitanyText
{
    /// <summary>O verbo do comando (colher, arrancar, cavar mudam pelo recurso).</summary>
    public static string Verb(LitanyCommand c, GameData data) => c.Verb switch
    {
        LitanyVerb.GoTo => "ir até",
        LitanyVerb.Take => "pegar",
        LitanyVerb.Put => "pôr",
        LitanyVerb.Gather => c.Target?.Resource switch
        {
            "rotten_shard" => "arrancar",
            string r when r == data.Castellan.Dig?.Item => "cavar",
            _ => "colher",
        },
        LitanyVerb.Operate => "operar",
        _ => "esperar",
    };

    /// <summary>O comando inteiro: "pegar Jarro d'água de Poço (2, 12)".</summary>
    public static string Command(LitanyCommand c, SimWorld world)
    {
        GameData data = world.Data;
        string item = c.Item is string i ? data.Item(i).Name.ToLowerInvariant() : "";
        return c.Verb switch
        {
            LitanyVerb.GoTo => $"ir até {Place(c.Target!, world)}",
            LitanyVerb.Take => $"pegar {item} de {Place(c.Target!, world)}",
            LitanyVerb.Put => $"pôr {item} em {Place(c.Target!, world)}",
            LitanyVerb.Gather => c.Target!.Anchored
                ? $"{Verb(c, data)} {ResourceName(c.Target.Resource!, data)} perto de {Place(new LitanyTarget(LitanyTargetKind.Building, c.Target.Cell), world)}"
                : $"{Verb(c, data)} {ResourceName(c.Target.Resource!, data)} perto de ({c.Target.Cell.X}, {c.Target.Cell.Z}), raio {c.Target.Radius:0}",
            LitanyVerb.Operate => $"operar {Place(c.Target!, world)}" + c.Until switch
            {
                OperateUntil.OutputFull => " até a saída encher",
                OperateUntil.NoInput => " até faltar insumo",
                _ => "",
            },
            _ => $"esperar {c.Ticks / (float)SimClock.TicksPerSecond:0.#} s",
        };
    }

    /// <summary>Por que travou, em palavras do jogo.</summary>
    public static string Stuck(LitanyStuck reason, LitanyCommand? c, SimWorld world)
    {
        string item = c?.Item is string i ? world.Data.Item(i).Name.ToLowerInvariant() : "o item";
        string place = c?.Target is LitanyTarget t && t.Kind == LitanyTargetKind.Building ? Place(t, world) : "o lugar";
        return reason switch
        {
            LitanyStuck.NoPath => "sem caminho",
            LitanyStuck.NoPlace => "o lugar sumiu",
            LitanyStuck.NoResource => $"não acho {(c?.Target?.Resource is string r ? ResourceName(r, world.Data) : "nada")} no raio",
            LitanyStuck.HandsFull => "mãos cheias",
            LitanyStuck.SourceEmpty => $"{place}: sem {item}",
            LitanyStuck.TargetFull => $"{place}: cheio",
            LitanyStuck.NotAccepted => $"{place} não usa {item}",
            LitanyStuck.NoPost => $"{place} não tem posto",
            LitanyStuck.PostTaken => "posto ocupado",
            _ => "pesado demais",
        };
    }

    /// <summary>Cor do bloco por tipo de comando.</summary>
    public static Color BlockColor(LitanyVerb verb) => verb switch
    {
        LitanyVerb.GoTo => new Color("4F7C9A"),
        LitanyVerb.Take => new Color("C0782E"),
        LitanyVerb.Put => new Color("A8612A"),
        LitanyVerb.Gather => new Color("6E8F3A"),
        LitanyVerb.Operate => Palette.PurpleLichen,
        _ => new Color("8C7A4E"),
    };

    private static string Place(LitanyTarget t, SimWorld world) => t.Kind == LitanyTargetKind.Building
        ? (world.BuildingAt(t.Cell) is Building b ? $"{b.Type.Name} ({t.Cell.X}, {t.Cell.Z})" : $"({t.Cell.X}, {t.Cell.Z}) — sumiu")
        : $"({t.Cell.X}, {t.Cell.Z})";

    private static string ResourceName(string kind, GameData data) =>
        kind == data.Castellan.Dig?.Item ? "argila" : data.Item(kind).Name.ToLowerInvariant();
}
