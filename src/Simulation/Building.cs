namespace Cidadela.Simulation;

/// <summary>
/// Construção colocada numa célula (esteira, baú, máquina). A direção é para onde a esteira leva
/// ou para onde a máquina solta o que produz.
/// </summary>
public sealed class Building
{
    public int Id { get; }
    public BuildingType Type { get; }
    public GridPos Cell { get; }
    public Direction Direction { get; }

    /// <summary>Itens andando nesta esteira, ou null se não é esteira.</summary>
    public BeltLane? Belt { get; }

    /// <summary>Itens guardados, ou null se não guarda (só baú).</summary>
    public Inventory? Storage { get; }

    /// <summary>Estado da receita, ou null se não é máquina.</summary>
    public MachineState? Machine { get; }

    /// <summary>Estado da mariposa, ou null se não é mariposa.</summary>
    public MothState? Moth { get; }

    /// <summary>Estado da cabana de trabalho, ou null se não é cabana.</summary>
    public Workplace? Workplace { get; }

    /// <summary>Quem ocupa cada posto (null = vago); vazio se a construção não tem postos.</summary>
    public Villager?[] Crew { get; }

    /// <summary>Quantos da equipe já chegaram e estão encostados trabalhando.</summary>
    public int CrewPresent
    {
        get
        {
            int n = 0;
            foreach (Villager? v in Crew)
                if (v is { Task: VillagerTask.AtPost } && v.Home == this)
                    n++;
            return n;
        }
    }

    /// <summary>Se todos os postos estão ocupados por quem já chegou (sem postos: sempre; carregadores não contam).</summary>
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

    /// <summary>Mana guardada (reservatório, como o Cristal-mãe).</summary>
    public float ManaStored { get; internal set; }

    public Building(int id, BuildingType type, GridPos cell, Direction direction, RecipeType? recipe = null)
    {
        Id = id;
        Type = type;
        Cell = cell;
        Direction = direction;
        if (type.IsBelt)
            Belt = new BeltLane();
        if (type.Storage)
            Storage = new Inventory();
        if (recipe is not null)
            Machine = new MachineState(recipe);
        if (type.Job is not null)
            Workplace = new Workplace(type.Job);
        if (type.Moth is not null)
            Moth = new MothState(type.Moth);
        Crew = new Villager?[type.Posts?.Count ?? type.Carriers?.Count ?? 0];
    }
}
