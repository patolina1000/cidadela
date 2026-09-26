using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Uma máquina trabalhando uma receita. Guarda entradas até 2 ciclos, trabalha quando tem tudo,
/// e acumula saídas até <see cref="OutputCycles"/> ciclos (depois para, esperando alguém tirar).
/// </summary>
public sealed class MachineState
{
    public const int InputCycles = 2;
    public const int OutputCycles = 5;

    public RecipeType Recipe { get; }
    public Inventory Input { get; } = new();
    public Inventory Output { get; } = new();
    public bool IsWorking { get; private set; }
    public int ProgressTicks { get; private set; }

    public float Progress => IsWorking ? (float)ProgressTicks / Recipe.Ticks : 0f;

    public MachineState(RecipeType recipe)
    {
        Recipe = recipe;
    }

    /// <summary>Se aceita mais 1 desse item na entrada.</summary>
    public bool Accepts(string kind) =>
        Recipe.Inputs.TryGetValue(kind, out int perCycle) && Input.Count(kind) < perCycle * InputCycles;

    /// <summary>Por que está parada: falta de entrada, saída cheia, ou null se está trabalhando.</summary>
    public MachineWait? Waiting =>
        IsWorking ? null : OutputFull ? MachineWait.OutputFull : MachineWait.MissingInput;

    private bool OutputFull
    {
        get
        {
            foreach ((string kind, int perCycle) in Recipe.Outputs)
                if (Output.Count(kind) + perCycle > perCycle * OutputCycles)
                    return true;
            return false;
        }
    }

    internal void Tick()
    {
        if (!IsWorking)
        {
            if (OutputFull || !Input.TryRemove(Recipe.Inputs))
                return;
            IsWorking = true;
            ProgressTicks = 0;
        }

        ProgressTicks++;
        if (ProgressTicks < Recipe.Ticks)
            return;

        Output.Add(Recipe.Outputs);
        IsWorking = false;
        ProgressTicks = 0;
    }

    /// <summary>Um item de saída para empurrar para fora (na ordem da receita), ou null.</summary>
    internal string? NextOutput()
    {
        foreach (string kind in Recipe.Outputs.Keys)
            if (Output.Count(kind) > 0)
                return kind;
        return null;
    }

    /// <summary>Tudo o que está dentro (entrada, saída e o ciclo em andamento) volta para o destino.</summary>
    internal void EmptyInto(Inventory target)
    {
        Input.MoveAllTo(target);
        Output.MoveAllTo(target);
        if (IsWorking)
            target.Add(Recipe.Inputs);
        IsWorking = false;
        ProgressTicks = 0;
    }
}

public enum MachineWait
{
    MissingInput,
    OutputFull,
}
