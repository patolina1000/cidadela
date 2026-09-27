using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenho de um aldeão com o modelo modular (GDD, "Aldeão: implementação v1"): um corpo-base careca
/// (<see cref="ModelPath"/>) com um rig e um conjunto de clipes só (idle, walk, carry, work, sleep), e três
/// encaixes presos à cabeça: "Rosto" (decal de expressão), "Cabelo" (peça sorteada) e "Chapéu" (peça de
/// cabeça). Estados da simulação → clipe: parado idle, andando walk, andando com carga carry, descansando
/// sleep. Coletando fica em idle com o golpe procedural do corpo (coleta e trabalho de máquina terão clipes
/// próprios; o clipe "work" da manivela não é usado na coleta, decisão de 27/09/2026).
/// A velocidade de walk/carry segue a velocidade real no chão pela passada medida no JSON do modelo, com um
/// teto (<see cref="MaxAnimationSpeed"/>): o aldeão anda mais rápido que a passada natural e o resto desliza.
/// Sem o modelo (arquivo faltando), cai na cápsula antiga.
/// </summary>
public partial class VillagerVisual : Node3D
{
    private const string ModelPath = "res://assets/modelos/aldeao_base/aldeao_base.glb";
    private const string ModelInfoPath = "res://assets/modelos/aldeao_base/aldeao_base.json";
    private const float TurnSmoothing = 12f;
    private const float SwingSmoothing = 30f;
    private const float ClipBlendSeconds = 0.15f;
    private const float StrideSmoothing = 10f;
    /// <summary>Teto da velocidade da animação em relação à passada natural (decisão de 27/09/2026).</summary>
    private const float MaxAnimationSpeed = 3f;
    private const float FallbackFaceWidth = 0.09f;
    // Decal do rosto: um pouco mais largo que o rosto medido; profundidade curta para não chegar à nuca.
    private const float FaceDecalScale = 1.15f;
    private const float FaceDecalDepth = 0.08f;

    /// <summary>Força o clipe sleep em todos (tecla N do painel de desempenho), só visual, para conferir o decal.</summary>
    public static bool DebugForceSleep { get; set; }

    /// <summary>Encaixe "Rosto": nó preso à cabeça, +Z para fora do rosto; null sem modelo.</summary>
    public Node3D? FaceSocket { get; private set; }
    /// <summary>Encaixe "Cabelo", no topo da cabeça.</summary>
    public Node3D? HairSocket { get; private set; }
    /// <summary>Encaixe "Chapéu", um pouco acima do cabelo.</summary>
    public Node3D? HatSocket { get; private set; }
    /// <summary>Largura do rosto em metros (extras do glTF), para o decal.</summary>
    public float FaceWidth { get; private set; } = FallbackFaceWidth;

    private Node3D _pivot = null!;
    private AnimationPlayer? _animations;
    private float _walkStride, _carryStride;
    private MeshInstance3D _load = null!;
    private StandardMaterial3D _loadMaterial = null!;
    private bool _lookApplied;
    private Node3D? _hair;
    private Node3D? _hairUnderHat;
    private VillagerLooks.Hair? _hairInfo;
    private Node3D? _hat;
    private string? _hatJob;
    private Decal? _face;
    private VillagerExpression? _shownExpression;
    private float _yaw;
    private float _swing;
    private float _bobPhase;
    private System.Numerics.Vector2 _lastDrawn;
    private bool _hasLast;

    public override void _Ready()
    {
        // Pivô nos pés: o golpe da coleta gira em volta do chão.
        _pivot = new Node3D { Name = "Pivot" };
        AddChild(_pivot);

        _loadMaterial = new StandardMaterial3D { Roughness = 0.9f };
        var loadMesh = new BoxMesh { Size = new Vector3(0.14f, 0.14f, 0.14f), Material = _loadMaterial };

        if (ResourceLoader.Exists(ModelPath) && GD.Load<PackedScene>(ModelPath) is PackedScene scene)
        {
            // O modelo olha para +Z (frente do glTF); o aldeão olha para -Z, como a protagonista.
            var model = scene.Instantiate<Node3D>();
            model.RotationDegrees = new Vector3(0f, 180f, 0f);
            _pivot.AddChild(model);

            _animations = model.FindChild("AnimationPlayer", recursive: true, owned: false) as AnimationPlayer;
            if (_animations is not null)
            {
                foreach (string clip in new[] { "idle", "walk", "carry", "work", "sleep" })
                {
                    if (_animations.HasAnimation(clip))
                        _animations.GetAnimation(clip).LoopMode = Animation.LoopModeEnum.Linear;
                }
                _animations.Play("idle");
            }

            FaceSocket = model.FindChild("Rosto", recursive: true, owned: false) as Node3D;
            HairSocket = model.FindChild("Cabelo", recursive: true, owned: false) as Node3D;
            HatSocket = (model.FindChild("Chapéu", recursive: true, owned: false) ?? model.FindChild("Chapeu", recursive: true, owned: false)) as Node3D;
            if (FaceSocket is not null && FaceSocket.HasMeta("largura_m"))
                FaceWidth = FaceSocket.GetMeta("largura_m").AsSingle();
            if (FaceSocket is null || HairSocket is null || HatSocket is null)
                GD.PushWarning($"Aldeão: encaixe faltando no modelo (Rosto={FaceSocket is not null}, Cabelo={HairSocket is not null}, Chapéu={HatSocket is not null}).");

            (_walkStride, _carryStride) = ReadStrides();

            // A carga fica abraçada à frente do corpo (o clipe carry trava os braços à frente, na altura do peito).
            _load = new MeshInstance3D { Name = "Load", Mesh = loadMesh, Position = new Vector3(0f, 0.2f, -0.13f), Visible = false };
            _pivot.AddChild(_load);
            return;
        }

        GD.PushWarning($"Aldeão: modelo {ModelPath} não encontrado; usando cápsula.");
        var body = new CapsuleMesh { Radius = 0.1f, Height = 0.4f };
        body.Material = new StandardMaterial3D { AlbedoColor = Palette.Bone, Roughness = 0.9f };
        _pivot.AddChild(new MeshInstance3D { Name = "Body", Mesh = body, Position = new Vector3(0f, 0.2f, 0f) });
        _load = new MeshInstance3D { Name = "Load", Mesh = loadMesh, Position = new Vector3(0f, 0.25f, 0.12f), Visible = false };
        _pivot.AddChild(_load);
    }

    /// <summary>
    /// O que a view precisa saber de um aldeão para desenhá-lo. O jogo monta a partir de <see cref="Villager"/>;
    /// a cena de estresse monta um sintético.
    /// </summary>
    public readonly record struct DrawState(
        System.Numerics.Vector2 Position, System.Numerics.Vector2 Facing, int HairVariant, VillagerExpression Expression,
        bool Resting, string? CarryingKind, string? JobResource, float GatherProgress, float GatherStep);

    public static DrawState StateOf(Villager villager, float alpha)
    {
        float step = 0f;
        if (villager.Task == VillagerTask.Gathering && villager.Target is ResourceNode node)
            step = 1f / Mathf.Max(1f, node.Type.GatherTicks * villager.Stats.GatherMultiplier);
        return new DrawState(
            System.Numerics.Vector2.Lerp(villager.PreviousPosition, villager.Position, alpha), villager.Facing,
            villager.HairVariant, villager.Expression, villager.Resting,
            villager.CarryingCount > 0 ? villager.CarryingKind : null,
            villager.Home?.Workplace?.Job.Resource,
            villager.Task == VillagerTask.Gathering ? Mathf.Clamp(villager.GatherProgress + alpha * step, 0f, 1f) : -1f, step);
    }

    public void UpdateFrom(Villager villager, GameData data, float alpha, float dt) => UpdateFrom(StateOf(villager, alpha), data, dt);

    public void UpdateFrom(in DrawState s, GameData data, float dt)
    {
        if (!_lookApplied)
            ApplyLook(s.HairVariant);
        UpdateHat(s.JobResource, data);
        if (_face is not null && _shownExpression != s.Expression)
        {
            _shownExpression = s.Expression;
            _face.TextureAlbedo = VillagerLooks.FaceTexture(s.Expression);
        }
        System.Numerics.Vector2 p = s.Position;
        Position = new Vector3(p.X + 0.5f, 0f, p.Y + 0.5f);

        float targetYaw = Mathf.Atan2(-s.Facing.X, -s.Facing.Y);
        _yaw = Mathf.LerpAngle(_yaw, targetYaw, 1f - Mathf.Exp(-TurnSmoothing * dt));
        Rotation = new Vector3(0f, _yaw, 0f);

        float walked = _hasLast ? System.Numerics.Vector2.Distance(_lastDrawn, p) : 0f;
        _lastDrawn = p;
        _hasLast = true;
        bool moving = walked > 0.0001f;
        bool carrying = s.CarryingKind is not null;

        _load.Visible = carrying;
        if (s.CarryingKind is string kind)
            _loadMaterial.AlbedoColor = Palette.ForItem(data, kind);

        // Golpe procedural só na coleta (sem clipe próprio ainda).
        float targetSwing = s.GatherProgress >= 0f ? CastellanVisual.SwingAngle(s.GatherProgress) : 0f;
        _swing = Mathf.Lerp(_swing, targetSwing, 1f - Mathf.Exp(-SwingSmoothing * dt));
        _pivot.Rotation = new Vector3(Mathf.DegToRad(_swing), 0f, 0f);

        if (_animations is null)
        {
            // Cápsula: quica ao andar.
            _bobPhase += walked * 1.4f * Mathf.Pi;
            _pivot.Position = new Vector3(0f, moving ? Mathf.Abs(Mathf.Sin(_bobPhase)) * 0.05f : 0f, 0f);
            return;
        }

        bool sleeping = s.Resting || DebugForceSleep;
        string clip = sleeping ? "sleep" : moving ? (carrying ? "carry" : "walk") : "idle";
        if (_animations.CurrentAnimation != clip && _animations.HasAnimation(clip))
            _animations.Play(clip, ClipBlendSeconds);

        // walk/carry no ritmo da velocidade real, até o teto; os outros clipes em 1×.
        float stride = clip == "walk" ? _walkStride : clip == "carry" ? _carryStride : 0f;
        float targetScale = 1f;
        if (stride > 0f && dt > 0f)
            targetScale = Mathf.Clamp(walked / dt / stride, 0f, MaxAnimationSpeed);
        _animations.SpeedScale = Mathf.Lerp(_animations.SpeedScale, targetScale, 1f - Mathf.Exp(-StrideSmoothing * dt));
    }

    /// <summary>Cabelo sorteado dentro do encaixe "Cabelo" (a peça já vem com a origem no encaixe).</summary>
    private void ApplyLook(int hairVariant)
    {
        _lookApplied = true;
        if (FaceSocket is not null)
        {
            // Decal projeta no seu -Y local; girado 90° em X, projeta no -Z do encaixe (para dentro do rosto).
            // Só atinge a camada 1 (o corpo); cabelo e chapéu ficam em outra camada.
            float side = FaceWidth * FaceDecalScale;
            _face = new Decal
            {
                Name = "Face",
                Size = new Vector3(side, FaceDecalDepth, side),
                RotationDegrees = new Vector3(90f, 0f, 0f),
                CullMask = 1u,
                AlbedoMix = 1f,
                NormalFade = 0.3f,
                UpperFade = 0.3f,
                LowerFade = 0.3f,
            };
            FaceSocket.AddChild(_face);
        }
        if (HairSocket is null)
            return;
        _hairInfo = VillagerLooks.HairFor(hairVariant);
        _hair = _hairInfo is null ? null : VillagerLooks.InstantiateHair(_hairInfo.Model);
        if (_hair is not null)
        {
            _hair.Name = "HairPiece";
            HairSocket.AddChild(_hair);
        }
    }

    /// <summary>
    /// Chapéu de quem tem cabana (peça "worker" de data/head_pieces.json, na cor do recurso do ofício) e a
    /// regra "cobre": nenhum mostra o cabelo; parcial troca pela versão sob chapéu (ou esconde, se não há);
    /// total esconde.
    /// </summary>
    private void UpdateHat(string? job, GameData data)
    {
        if (job == _hatJob)
            return;
        _hatJob = job;
        _hat?.QueueFree();
        _hat = null;
        _hairUnderHat?.QueueFree();
        _hairUnderHat = null;
        if (_hair is not null)
            _hair.Visible = true;

        if (job is null || HatSocket is null || VillagerLooks.WorkerPiece() is not VillagerLooks.HeadPiece piece)
            return;
        _hat = VillagerLooks.InstantiateHeadPiece(piece, Palette.ForItem(data, job));
        _hat.Name = "HatPiece";
        HatSocket.AddChild(_hat);

        if (piece.Covers == VillagerLooks.Coverage.None || _hair is null)
            return;
        _hair.Visible = false;
        if (piece.Covers == VillagerLooks.Coverage.Partial && _hairInfo is not null && !string.IsNullOrEmpty(_hairInfo.UnderHat))
        {
            _hairUnderHat = VillagerLooks.InstantiateHair(_hairInfo.UnderHat);
            if (_hairUnderHat is not null)
            {
                _hairUnderHat.Name = "HairUnderHat";
                HairSocket!.AddChild(_hairUnderHat);
            }
        }
    }

    /// <summary>Passadas (m/s) de walk e carry, medidas no Blender e gravadas no JSON do modelo; 0 se não houver.</summary>
    private static (float walk, float carry) ReadStrides()
    {
        if (!FileAccess.FileExists(ModelInfoPath))
            return (0f, 0f);
        var info = Json.ParseString(FileAccess.GetFileAsString(ModelInfoPath)).AsGodotDictionary();
        float walk = info.TryGetValue("passada_walk_m_s", out Variant w) ? w.AsSingle() : 0f;
        float carry = info.TryGetValue("passada_carry_m_s", out Variant c) ? c.AsSingle() : walk;
        return (walk, carry);
    }
}
