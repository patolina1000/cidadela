using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenho de um aldeão v2 (docs/aldeao_v2_contrato.md): o corpo da arte (aldeao_corpo.glb, girado 180°
/// porque a frente do glTF é +Z) com o material toon da pele, os retalhos "Olhos" e "Boca" com o shader do
/// rosto, e os encaixes que o jogo cria nos ossos: "Cabelo" e "Chapéu" na cabeça e "Peito" no peito, todos no
/// espaço do corpo em pose de repouso (a peça de cabelo, modelada nesse espaço, entra sem ajuste). Estados da
/// simulação → clipe (contrato de 29/09/2026, só idle e run por enquanto): andando e carregando → run; parado,
/// trabalhando (coletando, com o golpe procedural do corpo) e descansando → idle. Quando a arte entregar carry,
/// work e sleep, <see cref="ClipFor"/> passa a usá-los. O run toca no ritmo da velocidade real ÷ passada do
/// rosto.json, com teto (<see cref="MaxAnimationSpeed"/>).
/// Enquanto os arquivos da arte não existem (ou com <see cref="ForcePlaceholder"/>), desenha um placeholder:
/// cápsula com cabeça esférica, os dois retalhos curvos do rosto e um tufo de cabelo, com os mesmos materiais.
/// </summary>
public partial class VillagerVisual : Node3D
{
    private const float TurnSmoothing = 12f;
    private const float SwingSmoothing = 30f;
    private const float ClipBlendSeconds = 0.15f;
    private const float StrideSmoothing = 10f;
    /// <summary>
    /// Regra de velocidade (29/09/2026): a reprodução do run é velocidade ÷ passadaRun e fica entre 1,0× e
    /// 1,5×, para os pés não deslizarem nem a corrida parecer acelerada. A velocidade em data/ deve caber nisso.
    /// </summary>
    public const float MinAnimationSpeed = 1f, MaxAnimationSpeed = 1.5f;
    private const float PatchGap = 0.0015f; // retalhos 1,5 mm fora da pele (contrato: 1 a 2 mm)

    // Placeholder: cápsula de 0,30 m e cabeça de raio 0,095 (altura total ≈ 0,43 m, a do contrato).
    private const float BodyRadius = 0.085f, BodyHeight = 0.30f, HeadRadius = 0.095f, HeadY = 0.335f;

    /// <summary>Semente do piscar (o id do aldeão): cada um pisca no seu ritmo, sempre o mesmo.</summary>
    public int Seed { get; set; }

    /// <summary>Usa o placeholder mesmo que o corpo da arte exista (cena de teste do rosto).</summary>
    public bool ForcePlaceholder { get; set; }

    /// <summary>Clipe forçado em 1× (palco da Biografia); null = pelo estado da simulação.</summary>
    public string? PreviewClip { get; set; }

    /// <summary>Encaixe "Cabelo" (espaço do corpo em pose de repouso, preso ao osso da cabeça).</summary>
    public Node3D? HairSocket { get; private set; }
    /// <summary>Encaixe "Chapéu", mesmo espaço do cabelo.</summary>
    public Node3D? HatSocket { get; private set; }
    /// <summary>Encaixe "Peito" (cristal da classe, uso futuro).</summary>
    public Node3D? ChestSocket { get; private set; }
    /// <summary>Se está desenhando o placeholder (sem o corpo da arte).</summary>
    public bool IsPlaceholder { get; private set; }
    /// <summary>Se os olhos estão fechados por um piscar.</summary>
    public bool IsBlinking => _face?.Blinking ?? false;

    private Node3D _pivot = null!;
    private AnimationPlayer? _animations;
    private float _runStride;
    private Vector3 _headTop;
    private MeshInstance3D _load = null!;
    private StandardMaterial3D _loadMaterial = null!;
    private VillagerFace? _face;
    private bool _lookApplied;
    private Node3D? _hair, _hairUnderHat, _hat;
    private VillagerLooks.Hair? _hairInfo;
    private string? _hatJob;
    private float _yaw, _swing, _bobPhase;
    private System.Numerics.Vector2 _lastDrawn;
    private bool _hasLast;

    public override void _Ready()
    {
        _pivot = new Node3D { Name = "Pivot" };
        AddChild(_pivot);
        _loadMaterial = new StandardMaterial3D { AlbedoColor = Palette.Wood, Roughness = 0.9f };
        var loadMesh = new BoxMesh { Size = new Vector3(0.14f, 0.14f, 0.14f), Material = _loadMaterial };

        if (!ForcePlaceholder && VillagerLooks.HasBodyModel && VillagerLooks.BodyScene() is PackedScene scene)
        {
            BuildModel(scene.Instantiate<Node3D>());
            _load = new MeshInstance3D { Name = "Load", Mesh = loadMesh, Position = new Vector3(0f, 0.2f, -0.13f), Visible = false };
            _pivot.AddChild(_load);
            return;
        }

        IsPlaceholder = true;
        BuildPlaceholder();
        _load = new MeshInstance3D { Name = "Load", Mesh = loadMesh, Position = new Vector3(0f, 0.25f, -0.12f), Visible = false };
        _pivot.AddChild(_load);
    }

    // ---- corpo da arte ---------------------------------------------------------------------------------------

    private void BuildModel(Node3D model)
    {
        model.Name = "Model";
        model.RotationDegrees = new Vector3(0f, 180f, 0f); // frente do glTF em +Z; o aldeão olha para -Z
        _pivot.AddChild(model);
        VillagerLooks.FaceInfo info = VillagerLooks.Face();
        _runStride = info.StrideRun;

        MeshInstance3D? eyes = null, mouth = null;
        foreach (MeshInstance3D mesh in VillagerLooks.Descendants<MeshInstance3D>(model))
        {
            if (mesh.Name == "Olhos")
                eyes = mesh;
            else if (mesh.Name == "Boca")
                mouth = mesh;
            else
                mesh.MaterialOverride = VillagerLooks.SkinMaterial();
        }
        if (eyes is null || mouth is null)
            GD.PushWarning("Aldeão: o corpo não tem as malhas \"Olhos\" e \"Boca\" (contrato v2); rosto sem expressão.");
        _face = new VillagerFace(Seed, eyes, mouth);

        foreach (AnimationPlayer player in VillagerLooks.Descendants<AnimationPlayer>(model))
        {
            _animations = player;
            break;
        }
        if (_animations is null)
            GD.PushWarning("Aldeão: o corpo não tem AnimationPlayer; fica parado.");

        Skeleton3D? skeleton = null;
        foreach (Skeleton3D s in VillagerLooks.Descendants<Skeleton3D>(model))
        {
            skeleton = s;
            break;
        }
        if (skeleton is null)
        {
            GD.PushWarning("Aldeão: o corpo não tem Skeleton3D; sem encaixes de cabeça e peito.");
            return;
        }

        // Transformação do esqueleto em relação ao modelo: os encaixes ficam no espaço do corpo.
        Transform3D skeletonInModel = Transform3D.Identity;
        for (Node n = skeleton; n != model && n is Node3D n3; n = n.GetParent())
            skeletonInModel = n3.Transform * skeletonInModel;

        (HairSocket, HatSocket) = (Socket(skeleton, skeletonInModel, info.HeadBone, "Cabelo"), Socket(skeleton, skeletonInModel, info.HeadBone, "Chapéu"));
        ChestSocket = Socket(skeleton, skeletonInModel, info.ChestBone, "Peito");
        // Topo da cabeça (chapéu e tufo provisório): o osso "head_end" do rig da Meshy, ou o topo da malha.
        int headEnd = skeleton.FindBone("head_end");
        int head = skeleton.FindBone(info.HeadBone);
        _headTop = headEnd >= 0 ? (skeletonInModel * skeleton.GetBoneGlobalRest(headEnd)).Origin
            : head >= 0 ? (skeletonInModel * skeleton.GetBoneGlobalRest(head)).Origin + new Vector3(0f, 0.15f, 0f)
            : new Vector3(0f, 0.4f, 0f);
    }

    /// <summary>
    /// Encaixe preso a um osso, compensando a pose de repouso global do osso (e a do esqueleto no modelo):
    /// com o osso em repouso, o encaixe coincide com a origem do modelo, então uma peça modelada no espaço do
    /// corpo entra como filha sem ajuste e acompanha o osso quando ele se mexe.
    /// </summary>
    private static Node3D? Socket(Skeleton3D skeleton, Transform3D skeletonInModel, string boneName, string socketName)
    {
        int bone = skeleton.FindBone(boneName);
        if (bone < 0)
        {
            GD.PushWarning($"Aldeão: osso \"{boneName}\" não existe no esqueleto; sem o encaixe \"{socketName}\".");
            return null;
        }
        var attachment = new BoneAttachment3D { Name = socketName + "Attach", BoneName = boneName };
        skeleton.AddChild(attachment);
        var socket = new Node3D
        {
            Name = socketName,
            Transform = skeleton.GetBoneGlobalRest(bone).AffineInverse() * skeletonInModel.AffineInverse(),
        };
        attachment.AddChild(socket);
        return socket;
    }

    // ---- placeholder ------------------------------------------------------------------------------------------

    // Malhas do placeholder compartilhadas por todos os aldeões (como o corpo da arte será um GLB só).
    private static CapsuleMesh? _bodyMesh;
    private static SphereMesh? _headMesh, _hairMesh;
    private static ArrayMesh? _eyesPatch, _mouthPatch;

    private void BuildPlaceholder()
    {
        ShaderMaterial skin = VillagerLooks.SkinMaterial();
        _bodyMesh ??= new CapsuleMesh { Radius = BodyRadius, Height = BodyHeight };
        _headMesh ??= new SphereMesh { Radius = HeadRadius, Height = HeadRadius * 2f };
        _pivot.AddChild(new MeshInstance3D
        {
            Name = "Body",
            Mesh = _bodyMesh,
            MaterialOverride = skin,
            Position = new Vector3(0f, BodyHeight / 2f, 0f),
        });
        var head = new Node3D { Name = "Head", Position = new Vector3(0f, HeadY, 0f) };
        _pivot.AddChild(head);
        head.AddChild(new MeshInstance3D { Name = "Skull", Mesh = _headMesh, MaterialOverride = skin });

        // Retalhos curvos na frente da cabeça (-Z), com a proporção da célula de cada atlas.
        VillagerLooks.FaceInfo info = VillagerLooks.Face();
        const float eyesWidth = 0.11f, mouthWidth = 0.05f;
        _eyesPatch ??= Patch(eyesWidth, eyesWidth / info.Eyes.Aspect, HeadRadius + PatchGap, pitch: 0.12f);
        _mouthPatch ??= Patch(mouthWidth, mouthWidth / info.Mouth.Aspect, HeadRadius + PatchGap, pitch: -0.45f);
        var eyes = new MeshInstance3D { Name = "Olhos", Mesh = _eyesPatch };
        var mouth = new MeshInstance3D { Name = "Boca", Mesh = _mouthPatch };
        head.AddChild(eyes);
        head.AddChild(mouth);
        _face = new VillagerFace(Seed, eyes, mouth);

        // Encaixes no espaço do corpo (a cabeça do placeholder não se mexe).
        HairSocket = new Node3D { Name = "Cabelo", Position = new Vector3(0f, -HeadY, 0f) };
        HatSocket = new Node3D { Name = "Chapéu", Position = new Vector3(0f, -HeadY, 0f) };
        head.AddChild(HairSocket);
        head.AddChild(HatSocket);
        ChestSocket = new Node3D { Name = "Peito", Position = new Vector3(0f, 0.24f, -BodyRadius) };
        _pivot.AddChild(ChestSocket);
        _headTop = new Vector3(0f, HeadY + HeadRadius, 0f);
    }

    /// <summary>
    /// Retalho levemente curvo sobre uma esfera de raio <paramref name="radius"/> centrada na origem, virado para
    /// -Z, com <paramref name="pitch"/> radianos acima do equador; UV 0..1 cobre o retalho inteiro (a célula).
    /// </summary>
    private static ArrayMesh Patch(float width, float height, float radius, float pitch)
    {
        const int nx = 12, ny = 6;
        var st = new SurfaceTool();
        st.Begin(Mesh.PrimitiveType.Triangles);
        for (int j = 0; j <= ny; j++)
            for (int i = 0; i <= nx; i++)
            {
                float u = (float)i / nx, v = (float)j / ny;
                float yaw = (u - 0.5f) * width / radius;
                float elevation = pitch + (0.5f - v) * height / radius;
                var dir = new Vector3(-Mathf.Sin(yaw) * Mathf.Cos(elevation), Mathf.Sin(elevation), -Mathf.Cos(yaw) * Mathf.Cos(elevation));
                st.SetNormal(dir);
                st.SetUV(new Vector2(u, v));
                st.AddVertex(dir * radius);
            }
        for (int j = 0; j < ny; j++)
            for (int i = 0; i < nx; i++)
            {
                // No Godot a face da frente é a ordem horária.
                int a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1;
                st.AddIndex(a); st.AddIndex(b); st.AddIndex(c);
                st.AddIndex(b); st.AddIndex(d); st.AddIndex(c);
            }
        return st.Commit();
    }

    // ---- estado → desenho ------------------------------------------------------------------------------------

    /// <summary>
    /// O que a view precisa saber de um aldeão para desenhá-lo. O jogo monta a partir de <see cref="Villager"/>;
    /// a cena de teste do rosto e a de estresse montam um sintético.
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

    public void UpdateFrom(in DrawState s, GameData? data, float dt)
    {
        if (!_lookApplied)
            ApplyLook(s.HairVariant);
        UpdateHat(s.JobResource, data);
        _face?.Update(dt, s.Expression);

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
        if (s.CarryingKind is string kind && data is not null)
            _loadMaterial.AlbedoColor = Palette.ForItem(data, kind);

        // Golpe procedural só na coleta (sem clipe próprio ainda).
        float targetSwing = s.GatherProgress >= 0f ? CastellanVisual.SwingAngle(s.GatherProgress) : 0f;
        _swing = Mathf.Lerp(_swing, targetSwing, 1f - Mathf.Exp(-SwingSmoothing * dt));
        _pivot.Rotation = new Vector3(Mathf.DegToRad(_swing), 0f, 0f);

        if (_animations is null)
        {
            // Placeholder: quica ao andar e deita ao descansar.
            _bobPhase += walked * 1.4f * Mathf.Pi;
            float lie = s.Resting ? Mathf.DegToRad(-80f) : 0f;
            _pivot.Rotation = new Vector3(Mathf.DegToRad(_swing) + lie, 0f, 0f);
            _pivot.Position = new Vector3(0f, moving ? Mathf.Abs(Mathf.Sin(_bobPhase)) * 0.05f : s.Resting ? 0.08f : 0f, 0f);
            return;
        }

        string clip = PreviewClip ?? ClipFor(moving, carrying, s.Resting);
        if (_animations.CurrentAnimation != clip && _animations.HasAnimation(clip))
            _animations.Play(clip, ClipBlendSeconds);

        // Clipe de movimento no ritmo da velocidade real ÷ passada, preso entre 1,0× e 1,5×; os outros em 1×.
        float targetScale = 1f;
        if (PreviewClip is null && clip is "run" or "carry" && _runStride > 0f && dt > 0f)
            targetScale = Mathf.Clamp(walked / dt / _runStride, MinAnimationSpeed, MaxAnimationSpeed);
        if (data is not null)
            VillagerLooks.CheckSpeedRule(data.Villagers.CellsPerSecond);
        _animations.SpeedScale = Mathf.Lerp(_animations.SpeedScale, targetScale, 1f - Mathf.Exp(-StrideSmoothing * dt));
    }

    /// <summary>
    /// Clipe pelo estado. Hoje só existem idle e run (contrato de 29/09/2026). Quando a arte entregar os
    /// outros, a intenção é: carregando → "carry", descansando → "sleep", trabalhando em máquina → "work";
    /// basta trocar as linhas marcadas.
    /// </summary>
    private static string ClipFor(bool moving, bool carrying, bool resting)
    {
        if (resting)
            return "idle"; // aguardando o clipe "sleep"
        if (moving)
            return "run"; // carregando também: aguardando o clipe "carry"
        _ = carrying;
        return "idle";
    }

    /// <summary>Refaz cabelo e chapéu na próxima atualização (o palco da Biografia troca o cabelo ao vivo).</summary>
    public void ResetLook()
    {
        _lookApplied = false;
        _hair?.QueueFree();
        _hair = null;
        _hairUnderHat?.QueueFree();
        _hairUnderHat = null;
        _hatJob = "\0"; // valor que nenhum ofício tem: força o UpdateHat a refazer
    }

    /// <summary>Cabelo sorteado no encaixe "Cabelo"; sem o GLB (ou no placeholder), um tufo achatado na cor do cabelo.</summary>
    private void ApplyLook(int hairVariant)
    {
        _lookApplied = true;
        if (HairSocket is null)
            return;
        _hairInfo = VillagerLooks.HairFor(hairVariant);
        // Enquanto os outros cabelos não chegam, quem não tem o seu usa o primeiro que existir (hoje o cabelo 4).
        _hair = _hairInfo is not null && !IsPlaceholder ? VillagerLooks.InstantiateHairOrFallback(_hairInfo.Model) : null;
        if (_hair is null)
        {
            // Tufo provisório: calota um pouco diferente por variação, para as variações se distinguirem.
            float spread = 0.86f + 0.05f * hairVariant;
            _hairMesh ??= new SphereMesh { Radius = HeadRadius, Height = HeadRadius * 2f };
            _hair = new MeshInstance3D
            {
                Mesh = _hairMesh,
                MaterialOverride = VillagerLooks.HairMaterial(),
                Position = _headTop + new Vector3(0f, -HeadRadius * 0.3f, 0.02f),
                Scale = new Vector3(spread, 0.42f, spread), // calota só no alto da cabeça, longe dos olhos
            };
        }
        _hair.Name = "HairPiece";
        HairSocket.AddChild(_hair);
    }

    /// <summary>
    /// Chapéu de quem tem cabana (peça "worker" de data/head_pieces.json, na cor do recurso do ofício) e a
    /// regra "cobre": nenhum mostra o cabelo; parcial troca pela versão sob chapéu (ou esconde, se não há);
    /// total esconde.
    /// </summary>
    private void UpdateHat(string? job, GameData? data)
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
        Color color = data is not null ? Palette.ForItem(data, job) : Palette.Wheat;
        _hat = VillagerLooks.InstantiateHeadPiece(piece, color, _headTop);
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
}
