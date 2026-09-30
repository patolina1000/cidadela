namespace Cidadela.Simulation;

/// <summary>O que uma mariposa está fazendo: o item que leva e quanto do voo já fez.</summary>
public sealed class MothState
{
    public MothType Type { get; }

    /// <summary>O item que está levando, ou null.</summary>
    public string? Carrying { get; internal set; }

    /// <summary>Quanto do voo já fez, em ticks (vai até <see cref="MothType.Ticks"/>).</summary>
    public float FlightTicks { get; internal set; }

    /// <summary>Voando: levando um item e ainda não chegou (gasta a mana de voo; parada gasta a de espera).</summary>
    public bool Flying => Carrying is not null && FlightTicks < Type.Ticks;

    /// <summary>Progresso do voo, de 0 a 1 (0 parada).</summary>
    public float Progress => Carrying is null ? 0f : System.MathF.Min(1f, FlightTicks / Type.Ticks);

    /// <summary>Sem mana no último tick: pousou.</summary>
    public bool Landed { get; internal set; }

    public MothState(MothType type)
    {
        Type = type;
    }
}
