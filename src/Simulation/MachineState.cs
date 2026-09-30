using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Uma máquina trabalhando uma receita. Guarda entradas até <see cref="RecipeType.InputCycles"/> ciclos, trabalha quando
/// tem tudo e a equipe completa (<see cref="CrewReady"/>), e acumula saídas até <see cref="OutputCycles"/> ciclos (depois
/// para, esperando alguém tirar: a máquina nunca solta nada sozinha). O progresso anda <c>speed</c> ticks por tick (a
/// fração de mana da rede; 1 = normal, 0 = parada).
/// </summary>
public sealed class MachineState
{
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

    /// <summary>A fonte embaixo acabou (a mina sobre o veio esgotado): não começa ciclo novo. A simulação atualiza.</summary>
    public bool Exhausted { get; internal set; }

    /// <summary>Se começou um ciclo neste tick (a mina tira 1 do veio nessa hora).</summary>
    public bool StartedThisTick { get; private set; }

    private float _progress;

    public MachineState(RecipeType recipe)
    {
        Recipe = recipe;
    }

    /// <summary>Se aceita mais 1 desse item na entrada.</summary>
    public bool Accepts(string kind) => Room(kind) > 0;

    /// <summary>Quantos desse item ainda cabem na entrada (até 2 ciclos).</summary>
    public int Room(string kind) =>
        Recipe.Inputs.TryGetValue(kind, out int perCycle) ? System.Math.Max(0, perCycle * Recipe.InputCycles - Input.Count(kind)) : 0;

    /// <summary>
    /// Por que está parada, do mais forte ao mais fraco: posto vazio, veio esgotado, sem mana, saída cheia, falta de
    /// entrada; null se está trabalhando.
    /// </summary>
    public MachineWait? Waiting =>
        !CrewReady ? MachineWait.PostsEmpty
        : Exhausted && !IsWorking ? MachineWait.SourceDepleted
        : (IsWorking || CanStart) && Speed <= 0f ? MachineWait.NoMana
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
    public bool CanStart => !Exhausted && !OutputFull && Input.Has(Recipe.Inputs);

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
        StartedThisTick = false;
        if (!CrewReady)
            return;
        if (!IsWorking)
        {
            // Sem mana não começa (não gasta as entradas à toa).
            if (speed <= 0f || !CanStart || !Input.TryRemove(Recipe.Inputs))
                return;
            IsWorking = true;
            StartedThisTick = true;
            _progress = 0f;
        }

        _progress += speed;
        if (_progress < Recipe.Ticks - 0.0001f)
            return;

        Output.Add(Recipe.Outputs);
        IsWorking = false;
        _progress = 0f;
    }

    /// <summary>Um item pronto para tirar (na ordem da receita), ou null.</summary>
    public string? NextOutput()
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
    /// <summary>A rede não manda mana (fora de rede, ou rede sem geração).</summary>
    NoMana,
    /// <summary>A fonte embaixo acabou (veio esgotado).</summary>
    SourceDepleted,
}
