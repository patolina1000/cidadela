namespace Cidadela.Simulation;

/// <summary>
/// Troca a velocidade do Castelão, em células por segundo (teclas de depuração [ e ], temporárias: o Arthur ajusta
/// jogando e o valor escolhido vira o speed de data/castellan.json). Valores abaixo do mínimo ficam no mínimo.
/// </summary>
public sealed record SetCastellanSpeedCommand(float CellsPerSecond) : ISimCommand
{
    public const float Minimum = 0.1f;

    public void Apply(SimWorld world) => world.Castellan.SetSpeed(System.MathF.Max(CellsPerSecond, Minimum));
}
