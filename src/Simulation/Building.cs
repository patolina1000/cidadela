namespace Cidadela.Simulation;

/// <summary>
/// Construção colocada numa célula (baú, máquina, torre, cabana). A direção é só a do modelo (e para onde a cabana solta
/// no baú à frente).
/// </summary>
public sealed class Building
{
    public int Id { get; }
    public BuildingType Type { get; }
    public GridPos Cell { get; }
    public Direction Direction { get; }

    /// <summary>Itens guardados, ou null se não guarda (só baú).</summary>
    public Inventory? Storage { get; }

    /// <summary>Estado da receita, ou null se não é máquina.</summary>
    public MachineState? Machine { get; }

    /// <summary>Estado da cabana de trabalho, ou null se não é cabana.</summary>
    public Workplace? Workplace { get; }

    /// <summary>Quem ocupa cada posto (null = vago); vazio se a construção não tem postos.</summary>
    public Villager?[] Crew { get; }

    /// <summary>O posto que a protagonista ocupa (índice em <see cref="Crew"/>, que fica vazio nele), ou null.</summary>
    public int? CastellanSlot { get; internal set; }

    /// <summary>Quantos da equipe já chegaram e estão encostados trabalhando (a protagonista conta).</summary>
    public int CrewPresent
    {
        get
        {
            int n = 0;
            foreach (Villager? v in Crew)
                if (v is { Task: VillagerTask.AtPost } && v.Home == this)
                    n++;
            return CastellanSlot is null ? n : n + 1;
        }
    }

    /// <summary>Se todos os postos estão ocupados por quem já chegou (sem postos: sempre).</summary>
    public bool CrewReady => Type.Posts is null || CrewPresent == Crew.Length;

    public string Kind => Type.Kind;

    /// <summary>O recurso embaixo, de onde ela tira (a mina sobre o veio), ou null.</summary>
    public ResourceNode? Source { get; internal set; }

    /// <summary>A rede de mana em que está (dentro da área de uma torre, ou a própria torre), ou null.</summary>
    public ManaNetwork? Network { get; internal set; }

    /// <summary>
    /// Fração de mana que recebe agora (1 = tudo o que pede; 0 = nada, ou fora de rede). Quem não gasta mana recebe 1.
    /// </summary>
    public float ManaSatisfaction => Type.Mana is not { Use: > 0f } and not { IdleUse: > 0f } ? 1f : Network?.Satisfaction ?? 0f;

    /// <summary>Mana por segundo que pede neste tick (a simulação atualiza).</summary>
    public float ManaDemand { get; internal set; }

    /// <summary>Mana por segundo que gera neste tick (a simulação atualiza).</summary>
    public float ManaSupply { get; internal set; }

    /// <summary>Aldeões formados que ainda não acharam célula livre ao lado para nascer (o Cristal-mãe espera).</summary>
    public int PendingVillagers { get; internal set; }

    /// <summary>Quantos aldeões esta construção já formou.</summary>
    public int VillagersFormed { get; internal set; }

    /// <summary>Tick em que formou o último aldeão (-1 = nenhum).</summary>
    public long LastFormedTick { get; internal set; } = -1;

    public Building(int id, BuildingType type, GridPos cell, Direction direction, RecipeType? recipe = null)
    {
        Id = id;
        Type = type;
        Cell = cell;
        Direction = direction;
        if (type.Storage)
            Storage = new Inventory();
        if (recipe is not null)
            Machine = new MachineState(recipe);
        if (type.Job is not null)
            Workplace = new Workplace(type.Job);
        Crew = new Villager?[type.Posts?.Count ?? 0];
    }
}
