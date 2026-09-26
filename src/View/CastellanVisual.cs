using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenho do Castelão: o modelo da protagonista (assets/modelos/protagonista) com os clipes
/// idle, walk e work; sem o modelo, cápsula escura com "nariz" laranja. Anima só a partir do
/// estado da simulação: vira suave para a direção e, na cápsula, quica ao andar e dá golpes
/// sincronizados com a coleta (o golpe acerta quando o item cai).
/// </summary>
public partial class CastellanVisual : Node3D
{
    private const float TurnSmoothing = 15f;
    private const float SwingSmoothing = 30f;
    private const float BobHeight = 0.08f;
    private const float BobStepsPerCell = 1.1f;
    private const string ModelPath = "res://assets/modelos/protagonista/protagonista.glb";
    private const string ModelInfoPath = "res://assets/modelos/protagonista/protagonista.json";
    private const float ClipBlendSeconds = 0.15f;
    private const float StrideSmoothing = 10f;

    private Node3D _pivot = null!;
    private float _yaw;
    private float _swing;
    private float _bobPhase;
    private float _bob;
    private System.Numerics.Vector2 _lastDrawn;
    private bool _hasLast;
    private AnimationPlayer? _animations;
    private float _walkStride; // m/s em que o walk não desliza (medido no Blender); 0 = desconhecido

    public override void _Ready()
    {
        // Pivô nos pés: inclinar gira em volta do chão, não do meio do corpo.
        _pivot = new Node3D { Name = "Pivot" };
        AddChild(_pivot);

        if (ResourceLoader.Exists(ModelPath) && GD.Load<PackedScene>(ModelPath) is PackedScene scene)
        {
            // O modelo olha para +Z (frente de modelo do glTF); o Castelão olha para -Z.
            var model = scene.Instantiate<Node3D>();
            model.RotationDegrees = new Vector3(0f, 180f, 0f);
            _pivot.AddChild(model);
            _animations = model.FindChild("AnimationPlayer", recursive: true, owned: false) as AnimationPlayer;
            if (_animations is not null)
            {
                foreach (string clip in new[] { "idle", "walk", "work" })
                {
                    if (_animations.HasAnimation(clip))
                        _animations.GetAnimation(clip).LoopMode = Animation.LoopModeEnum.Linear;
                }
                _animations.Play("idle");
            }
            _walkStride = ReadWalkStride();
            return;
        }

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

        if (_animations is not null)
        {
            string clip = castellan.GatherTarget is not null ? "work" : walked > 0.0001f ? "walk" : "idle";
            if (_animations.CurrentAnimation != clip && _animations.HasAnimation(clip))
                _animations.Play(clip, ClipBlendSeconds);

            // O walk toca no ritmo da velocidade real no chão, para os pés não deslizarem
            // (inclusive ao frear numa parede).
            float targetScale = 1f;
            if (clip == "walk" && _walkStride > 0f && dt > 0f)
                targetScale = walked / dt / _walkStride;
            _animations.SpeedScale = Mathf.Lerp(_animations.SpeedScale, targetScale, 1f - Mathf.Exp(-StrideSmoothing * dt));
            return;
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

    private static float ReadWalkStride()
    {
        if (!FileAccess.FileExists(ModelInfoPath))
            return 0f;
        var info = Json.ParseString(FileAccess.GetFileAsString(ModelInfoPath)).AsGodotDictionary();
        return info.TryGetValue("passada_walk_m_s", out Variant stride) ? stride.AsSingle() : 0f;
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
