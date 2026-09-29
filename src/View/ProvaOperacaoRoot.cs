using System.Collections.Generic;
using System.Globalization;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Prova de operação (scenes/tests/ProvaOperacao.tscn), no padrão da VelocidadeAldeao: no crepúsculo do jogo, a
/// roda da variante r06 da arte e um aldeão em cada posto, cada um com o clipe próprio do posto (GLB separado,
/// carregado por <see cref="ExternalClips"/> em modo estrito). Tudo vem de
/// assets/modelos/prova_operacao/variante_r06/clipes.json, um bloco por posto (docs/animacao_contrato.md).
/// - A roda gira em volta do +Z local: −360° × fase (fase 0 = alça A no topo). O eixo da roda fica no X do mundo
///   para a câmera do jogo ver os dois de perfil.
/// - Cada aldeão é POSICIONADO pela fase da roda (seek): quadro = fase × quadros, sem inverter nem defasar.
/// - Golpe: quando a fase da roda passa por conta_na_fracao do clipe do posto. Teclas 1 e 2 tiram ou devolvem
///   cada um (dano simulado): fora do posto ele recua e fica em idle; ao voltar, entra no quadro da fase com
///   0,2 s de mistura. Abaixo do mínimo de operadores a roda desacelera até parar; com 1 ou 2 a velocidade é a
///   mesma.
/// - Câmera do jogo (55°), com zoom na roda do mouse até bem perto e Q/E para girar em passos de 45°.
/// - Mostra a distância palma-manopla de cada mão: a palma é a ponta do osso da mão com o comprimento medido
///   pela arte (girar_roda.json), e o alvo é a manopla ± 18 mm no X do aldeão, como no Blender.
/// </summary>
public partial class ProvaOperacaoRoot : Node3D
{
    private const string Dir = "res://assets/modelos/prova_operacao/variante_r06/";
    private const string ClipsJson = Dir + "clipes.json";
    private const string ReportJson = "res://assets/previews/prova_operacao/variante_r06/girar_roda.json";
    private const string Library = "operacao";
    // Meia distância entre as mãos na manopla (tools/arte/prova_operacao/operacao_lib.py, GRIP_HALF); não está nos JSON.
    private const float GripHalf = 0.018f;
    private const float StepBack = 0.45f; // quanto o aldeão recua ao sair do posto
    private const float WheelSmoothing = 2.5f; // desaceleração e aceleração da roda (1/s)
    private const int FieldSize = 20;
    private const float Pitch = 55f, DefaultDistance = 16f, MinZoom = 0.4f, MaxZoom = 16f, ZoomStep = 1.1f;

    /// <summary>Mínimo de operadores para a roda girar (teclas − e =).</summary>
    [Export] public int MinOperators = 1;
    /// <summary>Clipe de quem está fora do posto (teste: "run" para entrar no posto vindo da corrida).</summary>
    [Export] public string OffPostClip = "idle";

    private sealed class Operator
    {
        public required string Name;
        public required VillagerVisual Visual;
        public required Vector3 Post;
        public required Vector3 Forward;
        public required Vector3 HandleLocal;
        public required string Clip;
        public required float StrikeAt;
        public required Label3D Label;
        public bool OnPost = true;
        public int Strikes;
        public long LastCount;
        public float LeftMm = -1f, RightMm = -1f, TurnMaxMm, PrevTurnMaxMm = -1f;
        // Quantas vezes a roda passou pela fração do golpe; a roda só anda para a frente, então só cresce.
        public long Count(double wheel) => (long)Mathf.Floor(wheel - StrikeAt);
    }

    private readonly List<Operator> _ops = new();
    private readonly Dictionary<string, float> _durations = new(); // duracao_s de cada clipe, do clipes.json
    private GameData _data = null!;
    private Node3D _wheel = null!;
    private Vector3 _center;
    private Basis _wheelBasis;
    private double _phase;
    private float _speed, _turnSpeed, _handLeft, _handRight, _radius, _handleOut;
    private int _frames;
    private bool _paused;
    private long _lastTurn;
    private Camera3D _camera = null!;
    private Label _hud = null!;
    private float _zoom = 8f, _targetZoom = 8f, _yaw, _targetYaw;

    public override void _Ready()
    {
        _data = GameFiles.LoadData();
        var clips = Json.ParseString(FileAccess.GetFileAsString(ClipsJson)).AsGodotDictionary();
        var report = Json.ParseString(FileAccess.GetFileAsString(ReportJson)).AsGodotDictionary();
        var lengths = report["esqueleto"].AsGodotDictionary()["comprimentos_m"].AsGodotDictionary();
        _handLeft = lengths["LeftHand"].AsSingle();
        _handRight = lengths["RightHand"].AsSingle();
        _handleOut = report["roda"].AsGodotDictionary()["knob_y_m"].AsSingle();

        BuildGround();

        // A peça é a mesma em todos os blocos: o primeiro dá o arquivo, o raio, a duração e a altura do eixo
        // (os pés do posto estão a posicao_m.y do eixo).
        _wheelBasis = new Basis(Vector3.Up, Mathf.Pi / 2f);
        bool first = true;
        int seed = 1;
        foreach (Variant key in clips.Keys)
        {
            var clip = clips[key].AsGodotDictionary();
            var post = clip["posto"].AsGodotDictionary();
            var piece = clip["peca"].AsGodotDictionary();
            float[] p = post["posicao_m"].AsFloat32Array();
            var feetInWheel = new Vector3(p[0], p[1], p[2]);
            if (first)
            {
                first = false;
                _turnSpeed = 1f / clip["duracao_s"].AsSingle();
                _frames = clip["quadros"].AsInt32();
                _radius = piece["raio_alca_m"].AsSingle();
                _center = new Vector3(FieldSize / 2f, -feetInWheel.Y, FieldSize / 2f);
                _wheel = new Node3D { Name = "Roda", Position = _center, Basis = _wheelBasis };
                AddChild(_wheel);
                _wheel.AddChild(GD.Load<PackedScene>(Dir + piece["arquivo"].AsString()).Instantiate<Node3D>());
            }
            // Espaço do aldeão da arte (frente +Z) no espaço da roda: giro em Y do posto.
            Basis villager = _wheelBasis * new Basis(Vector3.Up, Mathf.DegToRad(post["giro_em_y_graus"].AsSingle()));
            Vector3 feet = _center + _wheelBasis * feetInWheel;
            // A alça A fica na face +Z da roda; a B, 180° depois, na face −Z.
            Vector3 handle = post["alca"].AsString() == "A" ? new Vector3(0f, _radius, _handleOut) : new Vector3(0f, -_radius, -_handleOut);
            _durations[key.AsString()] = clip["duracao_s"].AsSingle();
            AddOperator(post["nome"].AsString(), villager, feet, handle, Dir + clip["arquivo"].AsString(),
                clip["conta_na_fracao"].AsSingle(), seed);
            seed += 3;
        }

        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        PlaceCamera();

        var hud = new CanvasLayer { Name = "Hud" };
        AddChild(hud);
        _hud = new Label { Position = new Vector2(16f, 12f) };
        _hud.AddThemeFontSizeOverride("font_size", 17);
        _hud.AddThemeColorOverride("font_color", Palette.Bone);
        _hud.AddThemeColorOverride("font_outline_color", Colors.Black);
        _hud.AddThemeConstantOverride("outline_size", 5);
        hud.AddChild(_hud);

        // Primeiro quadro já no lugar: sem virar nem misturar desde o idle.
        foreach (Operator op in _ops)
            DrawOperator(op, 10f);
    }

    private void AddOperator(string name, Basis villagerSpace, Vector3 feet, Vector3 handleLocal, string clipGlb, float strikeAt, int seed)
    {
        feet.Y = 0f;
        Vector3 forward = villagerSpace * Vector3.Back; // +Z do glTF no mundo
        var visual = new VillagerVisual { Name = $"Aldeao{name}", Seed = seed };
        AddChild(visual);
        string library = $"{Library}_{name}";
        string clipName = "";
        if (visual.Animations is AnimationPlayer player)
        {
            List<string> added = ExternalClips.AddLibrary(player, clipGlb, library, _durations);
            if (added.Count > 0)
                clipName = added[0];
        }
        var label = new Label3D
        {
            Billboard = BaseMaterial3D.BillboardModeEnum.Enabled, NoDepthTest = true, FontSize = 40, PixelSize = 0.0022f,
            OutlineSize = 10, Modulate = Palette.Bone, OutlineModulate = new Color(0f, 0f, 0f, 0.8f),
            HorizontalAlignment = HorizontalAlignment.Center,
        };
        AddChild(label);
        var op = new Operator
        {
            Name = name, Visual = visual, Post = feet, Forward = forward, HandleLocal = handleLocal, Clip = clipName,
            StrikeAt = strikeAt, Label = label,
        };
        op.LastCount = op.Count(_phase);
        _ops.Add(op);
    }

    private void BuildGround()
    {
        AddChild(new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(FieldSize, FieldSize), Material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f } },
            Position = new Vector3(FieldSize / 2f, 0f, FieldSize / 2f),
        });
        var grass = new GrassField { Name = "Grass" };
        AddChild(grass);
        grass.Build(new WorldGrid(FieldSize, FieldSize), _data, _ => false);
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        switch (@event)
        {
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelUp }:
                _targetZoom = Mathf.Min(_targetZoom * ZoomStep, MaxZoom);
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelDown }:
                _targetZoom = Mathf.Max(_targetZoom / ZoomStep, MinZoom);
                break;
            case InputEventKey { Pressed: true, Echo: false } key:
                switch (key.PhysicalKeycode)
                {
                    case Key.Key1: Toggle(0); break;
                    case Key.Key2: Toggle(1); break;
                    case Key.Minus: MinOperators = Mathf.Max(MinOperators - 1, 0); break;
                    case Key.Equal: MinOperators = Mathf.Min(MinOperators + 1, _ops.Count); break;
                    case Key.Space: _paused = !_paused; break;
                    case Key.Q: _targetYaw -= Mathf.Pi / 4f; break;
                    case Key.E: _targetYaw += Mathf.Pi / 4f; break;
                    case Key.Escape: GetTree().ChangeSceneToFile(GameFiles.MenuScene); break;
                }
                break;
        }
    }

    /// <summary>Tira ou devolve um aldeão do posto (dano simulado).</summary>
    public void Toggle(int index)
    {
        if (index < 0 || index >= _ops.Count)
            return;
        Operator op = _ops[index];
        op.OnPost = !op.OnPost;
        op.LastCount = op.Count(_phase);
    }

    /// <summary>
    /// Troca o clipe de um posto por um GLB lido em tempo de execução (GLTFDocument, sem o importador do editor
    /// nem o otimizador dele), passando pelo mesmo <see cref="ExternalClips"/> estrito. Para testes: comparar com o
    /// clipe importado e provar a recusa de arquivos fora do contrato. Devolve quantos clipes entraram.
    /// </summary>
    public int LoadClipFile(int index, string path, int bakeFps)
    {
        Operator op = _ops[index];
        if (op.Visual.Animations is not AnimationPlayer player)
            return 0;
        var document = new GltfDocument();
        var state = new GltfState();
        if (document.AppendFromFile(path, state) != Error.Ok)
        {
            GD.PushWarning($"Clipes: não consegui ler {path}.");
            return 0;
        }
        Node root = document.GenerateScene(state, bakeFps);
        try
        {
            List<string> added = ExternalClips.AddLibrary(player, root, path, $"{Library}_{op.Name}_arquivo", _durations);
            if (added.Count > 0)
                op.Clip = added[0];
            return added.Count;
        }
        finally
        {
            root.Free();
        }
    }

    /// <summary>Fase acumulada da roda (voltas); pública para medir quadro a quadro com a roda pausada.</summary>
    public double Phase { get => _phase; set => _phase = value; }
    /// <summary>Roda parada (Espaço).</summary>
    public bool Paused { get => _paused; set => _paused = value; }
    /// <summary>Distâncias palma-manopla (mm) do aldeão 0 ou 1: esquerda, direita; −1 fora do posto.</summary>
    public Vector2 PalmMm(int index) => new(_ops[index].LeftMm, _ops[index].RightMm);

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        int operating = 0;
        foreach (Operator op in _ops)
            if (op.OnPost)
                operating++;
        float target = operating >= MinOperators ? _turnSpeed : 0f;
        _speed = Mathf.Lerp(_speed, target, 1f - Mathf.Exp(-WheelSmoothing * dt));
        if (target == 0f && _speed < 0.002f)
            _speed = 0f;
        if (!_paused)
            _phase += _speed * dt;
        _wheel.Basis = _wheelBasis * new Basis(Vector3.Back, -Mathf.Tau * (float)Mathf.PosMod(_phase, 1.0));

        long turn = (long)Mathf.Floor(_phase);
        bool newTurn = turn != _lastTurn;
        _lastTurn = turn;
        foreach (Operator op in _ops)
        {
            long count = op.Count(_phase);
            if (op.OnPost)
                op.Strikes += (int)System.Math.Max(count - op.LastCount, 0);
            op.LastCount = count;
            DrawOperator(op, dt);
            if (newTurn)
            {
                op.PrevTurnMaxMm = op.OnPost ? op.TurnMaxMm : -1f;
                op.TurnMaxMm = 0f;
            }
        }

        _zoom = Mathf.Lerp(_zoom, _targetZoom, 1f - Mathf.Exp(-8f * dt));
        _yaw = Mathf.Lerp(_yaw, _targetYaw, 1f - Mathf.Exp(-8f * dt));
        PlaceCamera();
        _hud.Text = HudText(operating);
    }

    private void DrawOperator(Operator op, float dt)
    {
        VillagerVisual v = op.Visual;
        Vector3 at = op.OnPost ? op.Post : op.Post - op.Forward * StepBack;
        if (op.OnPost && op.Clip.Length > 0)
        {
            v.PosedClip = op.Clip;
            v.PosedPhase = (float)Mathf.PosMod(_phase, 1.0);
            v.PreviewClip = null;
        }
        else
        {
            v.PosedClip = null;
            v.PreviewClip = OffPostClip;
        }
        var state = new VillagerVisual.DrawState(new System.Numerics.Vector2(at.X - 0.5f, at.Z - 0.5f),
            new System.Numerics.Vector2(op.Forward.X, op.Forward.Z), op.Name == "A" ? 1 : 3,
            op.OnPost ? VillagerExpression.Effort : VillagerExpression.Distracted, false, null, null, -1f, 0f);
        v.UpdateFrom(state, _data, dt);

        op.LeftMm = op.RightMm = -1f;
        if (op.OnPost && v.Skeleton is Skeleton3D skeleton && v.Model is Node3D model)
        {
            Vector3 handle = _wheel.GlobalTransform * op.HandleLocal;
            Vector3 side = model.GlobalBasis.X.Normalized() * GripHalf;
            op.LeftMm = (Palm(skeleton, "LeftHand", _handLeft) - (handle + side)).Length() * 1000f;
            op.RightMm = (Palm(skeleton, "RightHand", _handRight) - (handle - side)).Length() * 1000f;
            op.TurnMaxMm = Mathf.Max(op.TurnMaxMm, Mathf.Max(op.LeftMm, op.RightMm));
        }
        op.Label.Position = at - op.Forward * 0.25f + new Vector3(0f, 0.5f, 0f); // atrás de cada um: os dois não se cobrem
        op.Label.Text = $"{op.Name}: {op.Strikes} golpes" + (op.OnPost ? "" : "\nfora do posto");
    }

    /// <summary>Centro da palma no mundo: ponta do osso da mão (o eixo do osso é o Y local).</summary>
    private static Vector3 Palm(Skeleton3D skeleton, string bone, float length)
    {
        int index = skeleton.FindBone(bone);
        Transform3D pose = skeleton.GetBoneGlobalPose(index);
        float scale = skeleton.GlobalBasis.Scale.X;
        return skeleton.GlobalTransform * (pose * new Vector3(0f, length / scale, 0f));
    }

    private string HudText(int operating)
    {
        var ci = CultureInfo.GetCultureInfo("pt-BR");
        string Mm(float mm) => mm < 0f ? "—" : mm.ToString("0.0", ci) + " mm";
        var lines = new List<string>
        {
            $"Prova de operação  ·  roda r06 (alça a {_radius.ToString("0.00", ci)} m)  ·  um clipe por posto ({(1f / _turnSpeed).ToString("0.0", ci)} s por volta)  ·  {Engine.GetFramesPerSecond():0} FPS",
            $"fase da roda {Mathf.PosMod(_phase, 1.0).ToString("0.000", ci)}  ·  {_speed.ToString("0.00", ci)} volta/s  ·  voltas {_lastTurn}  ·  operadores {operating} (mínimo {MinOperators}){(_paused ? "  ·  PAUSADA" : "")}",
        };
        foreach (Operator op in _ops)
        {
            string where = op.Clip.Length == 0 ? "CLIPE RECUSADO (ver o log)" : op.OnPost ? $"quadro {(Mathf.PosMod(_phase, 1.0) * _frames).ToString("0.0", ci)} de {_frames}" : "fora do posto";
            lines.Add($"{op.Name} ({op.Clip}): {where}  ·  golpes {op.Strikes}  ·  palma-manopla esq {Mm(op.LeftMm)}, dir {Mm(op.RightMm)}  ·  máx da última volta {Mm(op.OnPost ? op.PrevTurnMaxMm : -1f)}");
        }
        lines.Add("1 e 2 tiram ou devolvem cada aldeão  ·  − e = mudam o mínimo de operadores  ·  Espaço pausa a roda  ·  roda do mouse aproxima  ·  Q e E giram a câmera  ·  Esc volta ao menu");
        return string.Join("\n", lines);
    }

    private void PlaceCamera()
    {
        float pitch = Mathf.DegToRad(Pitch);
        Vector3 lookAt = new(_center.X, 0.15f, _center.Z);
        var offset = new Vector3(0f, Mathf.Sin(pitch), Mathf.Cos(pitch)).Rotated(Vector3.Up, _yaw);
        _camera.Position = lookAt + offset * (DefaultDistance / _zoom);
        _camera.LookAt(lookAt, Vector3.Up);
    }
}
