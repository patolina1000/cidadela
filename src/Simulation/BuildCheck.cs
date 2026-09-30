namespace Cidadela.Simulation;

/// <summary>Resultado de "dá para construir aqui?". A cena usa para pintar a prévia; a simulação, para aceitar.</summary>
public enum BuildCheck
{
    Ok,
    OutOfBounds,
    OutOfReach,
    Occupied,
    NotEnoughItems,
    /// <summary>Construção na água (nada se constrói nela).</summary>
    WrongGround,
}
