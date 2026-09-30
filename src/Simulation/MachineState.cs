using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Uma máquina trabalhando uma receita. Guarda entradas até 2 ciclos, trabalha quando tem tudo e a equipe completa
/// (<see cref="CrewReady"/>), e acumula saídas até <see cref="OutputCycles"/> ciclos (depois para, esperando alguém
/// tirar). O progresso anda <c>speed</c> ticks por tick (1 = normal).
/// </summary>
public sealed class MachineState
{
    public const int InputCycles = 2;
    public const int OutputCycles = 5;

    public RecipeType Recipe { get; }
    public Inventory Input { get; } = new();
    public Inventory Output { get; } = new();
    public bool IsWorking { get; private set; }

    /// <summary>Se os postos da máquina estão todos ocupados por quem já chegou (a simulação atualiza a cada tick).</summary>
    public bool CrewReady { get; internal set; } = true;

    /// <summary>Velocidade do último tick (1 = normal).</summary>
    public float Speed { get; internal set; } = 1f;

    public float Progress => IsWorking ? _progress / Recipe.Ticks : 0f;

    private float _progress;

    public MachineState(RecipeType recipe)
    {
        Recipe = recipe;
    }

    /// <summary>Se aceita mais 1 desse item na entrada.</summary>
    public bool Accepts(string kind) => Room(kind) > 0;

    /// <summary>Quantos desse item ainda cabem na entrada (até 2 ciclos).</summary>
    public int Room(string kind) =>
        Recipe.Inputs.TryGetValue(kind, out int perCycle) ? System.Math.Max(0, perCycle * InputCycles - Input.Count(kind)) : 0;

    /// <summary>
    /// Por que está parada, do mais forte ao mais fraco: posto vazio, saída cheia, falta de entrada; null se está
    /// trabalhando.
    /// </summary>
    public MachineWait? Waiting =>
        !CrewReady ? MachineWait.PostsEmpty
        : IsWorking ? null
        : OutputFull ? MachineWait.OutputFull
        : MachineWait.MissingInput;

    /// <summary>O primeiro item da receita que falta para o próximo ciclo, ou null.</summary>
    public string? MissingItem
    {
        get
        {
            foreach ((string kind, int perCycle) in Recipe.Inputs)
                if (Input.Count(kind) < perCycle)
                    return kind;
            return null;
        }
    }

    /// <summary>Se começaria um ciclo agora (tem as entradas e a saída tem espaço), sem olhar a equipe.</summary>
    public bool CanStart => !OutputFull && Input.Has(Recipe.Inputs);

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

    internal void Tick(float speed = 1f)
    {
        Speed = speed;
        if (!CrewReady)
            return;
        if (!IsWorking)
        {
            if (OutputFull || !Input.TryRemove(Recipe.Inputs))
                return;
            IsWorking = true;
            _progress = 0f;
        }

        _progress += speed;
        if (_progress < Recipe.Ticks - 0.0001f)
            return;

        Output.Add(Recipe.Outputs);
        IsWorking = false;
        _progress = 0f;
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
        _progress = 0f;
    }
}

public enum MachineWait
{
    MissingInput,
    OutputFull,
    /// <summary>Falta gente nos postos (ou quem foi chamado ainda não chegou).</summary>
    PostsEmpty,
}
