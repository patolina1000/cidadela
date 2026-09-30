using System;

namespace Cidadela.Simulation;

/// <summary>
/// Converte o tempo real de cada frame num número inteiro de ticks fixos.
/// Parado (GDD, seção 3: botão de pausa), nenhum tick roda; o tick continua de 50 ms.
/// </summary>
public sealed class SimClock
{
    public const int TicksPerSecond = 20;
    public const double TickSeconds = 1.0 / TicksPerSecond;

    // Evita a "espiral da morte": se um frame travar, descartamos o atraso em vez de acumular.
    private const int MaxTicksPerFrame = 5;

    private double _accumulator;

    /// <summary>Fração (0..1) do caminho entre o último tick e o próximo, para interpolar o desenho.</summary>
    public double Alpha => _accumulator / TickSeconds;

    /// <summary>Parado: nenhum tick roda e o <see cref="Alpha"/> fica onde estava, então o desenho congela.</summary>
    public bool Paused { get; set; }

    public int Advance(double deltaSeconds)
    {
        if (Paused)
            return 0;
        _accumulator += Math.Max(0.0, deltaSeconds);
        int ticks = (int)(_accumulator / TickSeconds);
        if (ticks > MaxTicksPerFrame)
        {
            ticks = MaxTicksPerFrame;
            _accumulator = 0.0;
        }
        else
        {
            _accumulator -= ticks * TickSeconds;
        }
        return ticks;
    }
}
