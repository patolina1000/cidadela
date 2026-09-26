using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenho do Castelão: cápsula escura com "nariz" laranja. Anima só a partir do estado da
/// simulação: vira suave para a direção, quica ao andar e dá golpes sincronizados com a coleta
/// (o golpe acerta quando o item cai).
/// </summary>
public partial class CastellanVisual : Node3D
{
    private const float TurnSmoothing = 15f;
    private const float SwingSmoothing = 30f;
    private const float BobHeight = 0.08f;
    private const float BobStepsPerCell = 1.1f;

    private Node3D _pivot = null!;
    private float _yaw;
    private float _swing;
    private float _bobPhase;
    private float _bob;
    private System.Numerics.Vector2 _lastDrawn;
    private bool _hasLast;

    public override void _Ready()
    {
        // Pivô nos pés: inclinar gira em volta do chão, não do meio do corpo.
        _pivot = new Node3D { Name = "Pivot" };
        AddChild(_pivot);

        var body = new CapsuleMesh { Radius = 0.3f, Height = 1.2f };
        body.Material = new StandardMaterial3D { AlbedoColor = Palette.DeepPurple, Roughness = 0.8f };
        _pivot.AddChild(new MeshInstance3D { Name = "Body", Mesh = body, Position = new Vector3(0f, 0.6f, 0f) });

        var nose = new BoxMesh { Size = new Vector3(0.14f, 0.14f, 0.25f) };
        nose.Material = new StandardMaterial3D { AlbedoColor = Palette.Pumpkin, Roughness = 0.8f };
        _pivot.AddChild(new MeshInstance3D { Name = "Nose", Mesh = nose, Position = new Vector3(0f, 0.9f, -0.35f) });
    }

    public void UpdateFrom(Castellan castellan, float alpha, float dt)
    {
        System.Numerics.Vector2 p = System.Numerics.Vector2.Lerp(castellan.PreviousPosition, castellan.Position, alpha);
        Position = new Vector3(p.X + 0.5f, 0f, p.Y + 0.5f);

        // Virar suave: o nariz fica em -Z local, então yaw = atan2(-x, -z) da direção.
        float targetYaw = Mathf.Atan2(-castellan.Facing.X, -castellan.Facing.Y);
        _yaw = Mathf.LerpAngle(_yaw, targetYaw, 1f - Mathf.Exp(-TurnSmoothing * dt));
        Rotation = new Vector3(0f, _yaw, 0f);

        // Quicar pela distância andada, para o passo acompanhar a velocidade.
        float walked = _hasLast ? System.Numerics.Vector2.Distance(_lastDrawn, p) : 0f;
        _lastDrawn = p;
        _hasLast = true;
        if (walked > 0.0001f)
        {
            _bobPhase += walked * BobStepsPerCell * Mathf.Pi;
            _bob = Mathf.Abs(Mathf.Sin(_bobPhase)) * BobHeight;
        }
        else
        {
            _bob = Mathf.Lerp(_bob, 0f, 1f - Mathf.Exp(-12f * dt));
        }

        float targetSwing = 0f;
        if (castellan.GatherTarget is ResourceNode node)
        {
            float progress = castellan.GatherProgress + alpha / node.Type.GatherTicks;
            targetSwing = SwingAngle(Mathf.Clamp(progress, 0f, 1f));
        }
        _swing = Mathf.Lerp(_swing, targetSwing, 1f - Mathf.Exp(-SwingSmoothing * dt));

        _pivot.Position = new Vector3(0f, _bob, 0f);
        _pivot.Rotation = new Vector3(Mathf.DegToRad(_swing), 0f, 0f);
    }

    /// <summary>
    /// Graus de inclinação ao longo de um item: puxa para trás (positivo), bate para a frente
    /// (negativo) no fim e segura até o item cair.
    /// </summary>
    internal static float SwingAngle(float p)
    {
        const float back = 14f;
        const float strike = -28f;
        if (p < 0.7f)
            return back * Mathf.SmoothStep(0f, 1f, p / 0.7f);
        if (p < 0.85f)
        {
            float t = (p - 0.7f) / 0.15f;
            return Mathf.Lerp(back, strike, t * t);
        }
        return strike;
    }
}
