using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>
/// Direção em que o Castelão deve andar, já em coordenadas do mundo (X, Z), e se está correndo.
/// Zero = parar. A conversão da câmera para o mundo é trabalho da cena.
/// </summary>
public sealed record MoveCommand(Vector2 Direction, bool Run = false) : ISimCommand
{
    public void Apply(SimWorld world) => world.Castellan.SetMoveDirection(Direction, Run);
}
