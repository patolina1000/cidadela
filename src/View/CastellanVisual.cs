using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenho do Castelão: a protagonista v2 (assets/modelos/protagonista_v2, <see cref="ProtagonistV2Model"/>) com os clipes
/// idle-loop e run-loop (ela só corre) e o rosto com expressão pelo estado (coletando: esforço; senão, neutra cansada);
/// com <see cref="UseV1"/>, a v1 (assets/modelos/protagonista, clipes idle, run e work), para a cena de comparação; sem
/// modelo, cápsula escura com "nariz" laranja. Anima só a partir do estado da simulação: vira suave para a direção e, na
/// cápsula, quica ao andar e dá golpes sincronizados com a coleta (o golpe acerta quando o item cai).
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
    private const string ChestBone = "Spine";
    private const float CrystalEmissionBoost = 3f;
    private static readonly Color CrystalLightColor = new(0.35f, 0.55f, 1f);
    // Camada de render só da protagonista: a luz do cristal ignora essa camada (clareia o chão e o que
    // está em volta, não o próprio cabelo e corpo). Sol, ambiente e câmera continuam vendo todas.
    private const uint SelfLayer = 1u << 19;
    private const float CrystalLightSpecular = 0.1f;

    private AnimationPlayer? _animations;
    private float _runStride; // m/s em que o run não desliza (medido no Blender); 0 = desconhecido
    private ProtagonistFace? _face;
    private string _idleClip = "idle", _runClip = "run", _workClip = "work";

    /// <summary>Desenha a v1 no lugar da v2 (só a cena de comparação usa).</summary>
    [Export] public bool UseV1 { get; set; }

    public override void _Ready()
    {
        // Pivô nos pés: inclinar gira em volta do chão, não do meio do corpo.
        _pivot = new Node3D { Name = "Pivot" };
        AddChild(_pivot);

        if (!UseV1 && ProtagonistV2Model.Available)
        {
            ProtagonistV2Model.Built v2 = ProtagonistV2Model.Build(_pivot, SelfLayer);
            _animations = v2.Animations;
            _face = v2.Face;
            _runStride = v2.RunStride;
            (_idleClip, _runClip, _workClip) = (ProtagonistV2Model.IdleClip, ProtagonistV2Model.RunClip, ProtagonistV2Model.IdleClip);
            _animations?.Play(_idleClip);
            return;
        }

        if (ResourceLoader.Exists(ModelPath) && GD.Load<PackedScene>(ModelPath) is PackedScene scene)
        {
            // O modelo olha para +Z (frente de modelo do glTF); o Castelão olha para -Z.
            var model = scene.Instantiate<Node3D>();
            model.RotationDegrees = new Vector3(0f, 180f, 0f);
            _pivot.AddChild(model);
            _animations = model.FindChild("AnimationPlayer", recursive: true, owned: false) as AnimationPlayer;
            if (_animations is not null)
            {
                foreach (string clip in new[] { "idle", "run", "work" })
                {
                    if (_animations.HasAnimation(clip))
                        _animations.GetAnimation(clip).LoopMode = Animation.LoopModeEnum.Linear;
                }
                _animations.Play("idle");
            }
            _runStride = ReadStride("passada_run_m_s");
            AddCrystalGlow(model);
            return;
        }

        var body = new CapsuleMesh { Radius = 0.3f, Height = 1.2f };
        body.Material = new StandardMaterial3D { AlbedoColor = Palette.DeepPurple, Roughness = 0.8f };
        _pivot.AddChild(new MeshInstance3D { Name = "Body", Mesh = body, Position = new Vector3(0f, 0.6f, 0f) });

        var nose = new BoxMesh { Size = new Vector3(0.14f, 0.14f, 0.25f) };
        nose.Material = new StandardMaterial3D { AlbedoColor = Palette.Pumpkin, Roughness = 0.8f };
        _pivot.AddChild(new MeshInstance3D { Name = "Nose", Mesh = nose, Position = new Vector3(0f, 0.9f, -0.35f) });
    }

    /// <summary>
    /// Toca um clipe em 1× fora da simulação (palco da Biografia, menu, cena de comparação): "idle", "run" ou "work" (na
    /// v2, "work" é o idle: ela ainda não tem clipe de trabalho). Sem efeito na cápsula.
    /// </summary>
    public void PlayClip(string clip)
    {
        string name = clip switch { "idle" => _idleClip, "run" => _runClip, "work" => _workClip, _ => clip };
        if (_animations is null || !_animations.HasAnimation(name))
            return;
        _animations.Play(name, ClipBlendSeconds);
        _animations.SpeedScale = 1f;
    }

    /// <summary>Clipes que este modelo tem, pelos nomes lógicos (a Biografia mostra só esses botões).</summary>
    public bool HasClip(string clip) => clip switch
    {
        "work" => _animations?.HasAnimation(_workClip) == true && _workClip != _idleClip,
        "idle" => _animations?.HasAnimation(_idleClip) == true,
        "run" => _animations?.HasAnimation(_runClip) == true,
        _ => _animations?.HasAnimation(clip) == true,
    };

    public override void _Process(double delta)
    {
        // O rosto pisca e segue a expressão mesmo fora do jogo (menu, Biografia).
        _face?.Update((float)delta, _expression);
    }

    private string _expression = ProtagonistFace.Neutral;

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
            bool moving = walked > 0.0001f;
            string clip = castellan.GatherTarget is not null ? _workClip : moving ? _runClip : _idleClip;
            _expression = castellan.GatherTarget is not null ? ProtagonistFace.Effort : ProtagonistFace.Neutral;
            if (_animations.CurrentAnimation != clip && _animations.HasAnimation(clip))
                _animations.Play(clip, ClipBlendSeconds);

            // O run toca no ritmo da velocidade real no chão, para os pés não deslizarem
            // (inclusive ao frear numa parede).
            float stride = clip == _runClip ? _runStride : 0f;
            float targetScale = 1f;
            if (stride > 0f && dt > 0f)
                targetScale = walked / dt / stride;
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

    /// <summary>
    /// No crepúsculo (GDD, seção 17) a protagonista some no chão escuro: o cristal do peito brilha mais
    /// e acende uma luz azul suave em volta dela, presa ao osso do peito para acompanhar a corrida.
    /// Sem sombra: a luz sai "de dentro" do corpo e só clareia o chão e o que está perto. Ela não
    /// ilumina a própria protagonista (camada <see cref="SelfLayer"/>): colada ao peito, deixava o
    /// cabelo e o corpo brilhando demais.
    /// </summary>
    private static void AddCrystalGlow(Node3D model)
    {
        foreach (Node node in model.FindChildren("*", nameof(MeshInstance3D), recursive: true, owned: false))
        {
            var mesh = (MeshInstance3D)node;
            mesh.Layers = SelfLayer;
            for (int i = 0; i < mesh.GetSurfaceOverrideMaterialCount(); i++)
            {
                if (mesh.Mesh.SurfaceGetMaterial(i) is StandardMaterial3D { ResourceName: "Cristal" } crystal)
                {
                    var brighter = (StandardMaterial3D)crystal.Duplicate();
                    brighter.EmissionEnergyMultiplier = crystal.EmissionEnergyMultiplier * CrystalEmissionBoost;
                    mesh.SetSurfaceOverrideMaterial(i, brighter);
                }
                else if (mesh.Mesh.SurfaceGetMaterial(i) is Material original)
                {
                    // Contorno fino escuro (Outline) no corpo e no cabelo; cópia, para não mexer no material importado.
                    var outlined = (Material)original.Duplicate();
                    Outline.Attach(outlined);
                    mesh.SetSurfaceOverrideMaterial(i, outlined);
                }
            }
        }

        var light = new OmniLight3D
        {
            Name = "CrystalLight",
            LightColor = CrystalLightColor,
            LightEnergy = 0.85f,
            OmniRange = 2.3f,
            OmniAttenuation = 1.4f,
            ShadowEnabled = false,
            LightSpecular = CrystalLightSpecular,
            LightCullMask = ~SelfLayer,
        };
        if (model.FindChild("Skeleton3D", recursive: true, owned: false) is Skeleton3D skeleton &&
            skeleton.FindBone(ChestBone) >= 0)
        {
            var chest = new BoneAttachment3D { Name = "Chest", BoneName = ChestBone };
            skeleton.AddChild(chest);
            chest.AddChild(light);
        }
        else
        {
            light.Position = new Vector3(0f, 0.55f, 0f);
            model.AddChild(light);
        }
    }

    /// <summary>Passada (m/s) de um clipe, medida no Blender e gravada no JSON do modelo; 0 se não houver.</summary>
    private static float ReadStride(string key)
    {
        if (!FileAccess.FileExists(ModelInfoPath))
            return 0f;
        var info = Json.ParseString(FileAccess.GetFileAsString(ModelInfoPath)).AsGodotDictionary();
        return info.TryGetValue(key, out Variant stride) ? stride.AsSingle() : 0f;
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
