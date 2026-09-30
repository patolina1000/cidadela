using System;

namespace Cidadela.Simulation;

/// <summary>
/// Converte o tempo real de cada frame num número inteiro de ticks fixos.
/// A pausa e a velocidade (GDD, seção 3) mudam quantos ticks rodam por frame; o tick continua de 50 ms.
/// </summary>
public sealed class SimClock
{
    public const int TicksPerSecond = 20;
    public const double TickSeconds = 1.0 / TicksPerSecond;

    // Evita a "espiral da morte": se um frame travar, descartamos o atraso em vez de acumular.
    // O limite cresce com a velocidade, senão o 3x nunca passaria de 5 ticks por frame.
    private const int MaxTicksPerFrame = 5;

    private double _accumulator;
    private int _speed = 1;

    /// <summary>Fração (0..1) do caminho entre o último tick e o próximo, para interpolar o desenho.</summary>
    public double Alpha => _accumulator / TickSeconds;

    /// <summary>Parado: nenhum tick roda e o <see cref="Alpha"/> fica onde estava, então o desenho congela.</summary>
    public bool Paused { get; set; }

    /// <summary>Multiplicador do tempo do jogo (1 = 20 ticks por segundo real).</summary>
    public int Speed
    {
        get => _speed;
        set => _speed = value >= 1 ? value : throw new ArgumentOutOfRangeException(nameof(value), "A velocidade é no mínimo 1.");
    }

    public int Advance(double deltaSeconds)
    {
        if (Paused)
            return 0;
        _accumulator += Math.Max(0.0, deltaSeconds) * _speed;
        int ticks = (int)(_accumulator / TickSeconds);
        int max = MaxTicksPerFrame * _speed;
        if (ticks > max)
        {
            ticks = max;
            _accumulator = 0.0;
        }
        else
        {
            _accumulator -= ticks * TickSeconds;
        }
        return ticks;
    }
}
