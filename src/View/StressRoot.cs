using System;
using System.Collections.Generic;
using System.Text;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Cena de teste de estresse (scenes/Stress.tscn): milhares de inimigos, máquinas e itens em esteiras com
/// formas simples, sobre o campo de grama e com a mesma luz e névoa do jogo. Compara dois jeitos de desenhar
/// o mesmo estado da <see cref="StressWorld"/>:
/// - <b>Nós</b> (como o jogo faz hoje): um MeshInstance3D por entidade, posicionado a cada quadro.
/// - <b>MultiMesh</b>: um MultiMesh por tipo de malha e por pedaço do mapa; a cada quadro só o buffer de
///   transformações de cada pedaço é reescrito, e pedaços fora da tela não são desenhados.
/// Teclas: M troca o modo, G liga/desliga a grama, F2 V-Sync, F3 painel, F11 captura, roda do mouse aproxima,
/// WASD anda com a câmera.
/// </summary>
public partial class StressRoot : Node3D
{
    [Export] public int FieldWidth = 80;
    [Export] public int FieldHeight = 80;
    [Export] public int Enemies = 5000;
    [Export] public int Machines = 500;
    [Export] public int Items = 10000;
    [Export] public bool WithGrass = true;
    [Export] public bool StartWithMultiMesh = true;
    /// <summary>Aldeões com o modelo modular completo (esqueleto animado, cabelo, decal, chapéu). Teclas 1/2/3: 50/200/500.</summary>
    [Export] public int Villagers = 0;

    private const int ChunkCells = 8;
    private const float Pitch = 55f;

    private enum Mode { Nodes, MultiMesh }

    private StressWorld _world = null!;
    private readonly SimClock _clock = new();
    private Mode _mode;
    private Camera3D _camera = null!;
    private Vector3 _lookAt;
    private float _distance = 16f;
    private Label _label = null!;
    private GrassField? _grass;
    private double _simMs, _viewMs, _accum;

    // Aldeões animados: andam em círculos, metade com chapéu (ofício), expressão trocando de vez em quando.
    private Node3D _villagersRoot = null!;
    private readonly List<VillagerVisual> _villagerVisuals = new();
    private readonly List<(System.Numerics.Vector2 center, float radius, float phase, int hair, string? job)> _villagerOrbits = new();
    private GameData? _gameData;
    private double _villagerClock;

    // Malhas compartilhadas (as mesmas nos dois modos).
    private Mesh[] _enemyMeshes = null!;
    private Mesh[] _itemMeshes = null!;
    private Mesh _machineBody = null!, _machineRoof = null!;

    // Modo nós.
    private Node3D _nodesRoot = null!;
    private MeshInstance3D[] _enemyNodes = null!;
    private MeshInstance3D[] _itemNodes = null!;

    // Modo MultiMesh: [tipo][pedaço].
    private Node3D _multiRoot = null!;
    private ChunkSet[] _enemySets = null!;
    private ChunkSet[] _itemSets = null!;
    private int _chunksX, _chunksZ;

    /// <summary>MultiMeshes de uma malha, um por pedaço, com buffer reutilizado e capacidade que só cresce.</summary>
    private sealed class ChunkSet
    {
        public MultiMeshInstance3D[] Nodes = null!;
        public float[][] Buffers = null!;
        public int[] Counts = null!;
        // Caixa justa do quadro (só X/Z; a altura é fixa por malha): o culling por pedaço fica exato.
        public float[] MinX = null!, MaxX = null!, MinZ = null!, MaxZ = null!;
        public float Height;
    }

    public override void _Ready()
    {
        // Medição só vale em tela cheia na Retina; a janela às vezes abre em 1152×648 quando lançada pelo editor.
        DisplayServer.WindowSetMode(DisplayServer.WindowMode.Fullscreen);
        _world = new StressWorld(FieldWidth, FieldHeight, Enemies, Machines, Items);
        _mode = StartWithMultiMesh ? Mode.MultiMesh : Mode.Nodes;
        _label = GetNode<Label>("Hud/Label");

        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        _lookAt = new Vector3(FieldWidth / 2f, 0f, FieldHeight / 2f);
        PlaceCamera();

        BuildGround();
        BuildMeshes();
        BuildNodes();
        BuildMultiMeshes();
        if (WithGrass)
            BuildGrass();
        _villagersRoot = new Node3D { Name = "Villagers" };
        AddChild(_villagersRoot);
        SetVillagerCount(Villagers);
        ApplyMode();
    }

    private GameData LoadGameData() => _gameData ??= GameData.Parse(
        FileAccess.GetFileAsString("res://data/items.json"),
        FileAccess.GetFileAsString("res://data/resources.json"),
        FileAccess.GetFileAsString("res://data/castellan.json"),
        FileAccess.GetFileAsString("res://data/villagers.json"),
        FileAccess.GetFileAsString("res://data/buildings.json"),
        FileAccess.GetFileAsString("res://data/recipes.json"),
        FileAccess.GetFileAsString("res://data/terrain.json"));

    /// <summary>Recria os aldeões animados: N em volta do centro da câmera, em círculos de raio 1,5 a 6.</summary>
    private void SetVillagerCount(int count)
    {
        foreach (VillagerVisual v in _villagerVisuals)
            v.QueueFree();
        _villagerVisuals.Clear();
        _villagerOrbits.Clear();
        Villagers = count;
        if (count == 0)
            return;
        GameData data = LoadGameData();
        string[] jobs = { "wood", "stone", "iron" };
        var rng = new RandomNumberGenerator { Seed = 99 };
        for (int i = 0; i < count; i++)
        {
            // Espalha em anéis em volta do ponto olhado, com densidade parecida com uma vila cheia.
            float ring = 1.5f + Mathf.Sqrt(rng.Randf()) * (2.5f + Mathf.Sqrt(count) * 0.55f);
            var center = new System.Numerics.Vector2(_lookAt.X - 0.5f + rng.RandfRange(-ring, ring), _lookAt.Z - 0.5f + rng.RandfRange(-ring, ring));
            _villagerOrbits.Add((center, rng.RandfRange(0.6f, 1.6f), rng.Randf() * Mathf.Tau, 1 + i % Villager.HairVariants, i % 2 == 0 ? jobs[i % 3] : null));
            var visual = new VillagerVisual { Name = $"StressVillager_{i}" };
            _villagersRoot.AddChild(visual);
            _villagerVisuals.Add(visual);
        }
    }

    private void RenderVillagers(float dt)
    {
        if (_villagerVisuals.Count == 0)
            return;
        _villagerClock += dt;
        GameData data = LoadGameData();
        const float speed = 1.2f; // células/s, a do jogo
        for (int i = 0; i < _villagerVisuals.Count; i++)
        {
            (System.Numerics.Vector2 center, float radius, float phase, int hair, string? job) = _villagerOrbits[i];
            float w = speed / radius;
            float a = phase + (float)_villagerClock * w;
            var pos = center + new System.Numerics.Vector2(Mathf.Cos(a), Mathf.Sin(a)) * radius;
            var facing = new System.Numerics.Vector2(-Mathf.Sin(a), Mathf.Cos(a));
            // Expressão muda a cada ~4 s, escalonada por aldeão; um quarto anda carregando.
            var expression = (VillagerExpression)(((int)(_villagerClock / 4.0) + i) % 9);
            string? carrying = i % 4 == 0 ? "wood" : null;
            var state = new VillagerVisual.DrawState(pos, facing, hair, expression, false, carrying, job, -1f, 0f);
            _villagerVisuals[i].UpdateFrom(state, data, dt);
        }
    }

    private void BuildGround()
    {
        var material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f };
        AddChild(new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(FieldWidth, FieldHeight), Material = material },
            Position = new Vector3(FieldWidth / 2f, 0f, FieldHeight / 2f),
        });
    }

    private void BuildGrass()
    {
        GameData data = GameData.Parse(
            FileAccess.GetFileAsString("res://data/items.json"),
            FileAccess.GetFileAsString("res://data/resources.json"),
            FileAccess.GetFileAsString("res://data/castellan.json"),
            FileAccess.GetFileAsString("res://data/villagers.json"),
            FileAccess.GetFileAsString("res://data/buildings.json"),
            FileAccess.GetFileAsString("res://data/recipes.json"),
            FileAccess.GetFileAsString("res://data/terrain.json"));
        var grid = new WorldGrid(FieldWidth, FieldHeight); // tudo grama (terreno 0)
        _grass = new GrassField { Name = "Grass" };
        AddChild(_grass);
        _grass.Build(grid, data, _world.IsOccupied);
    }

    private void BuildMeshes()
    {
        Color[] enemyColors = { Palette.Sickly, Palette.Pumpkin, Palette.Bone, Palette.Stone };
        _enemyMeshes = new Mesh[4];
        for (int k = 0; k < 4; k++)
            _enemyMeshes[k] = new CapsuleMesh { Radius = 0.2f, Height = 0.8f, Material = new StandardMaterial3D { AlbedoColor = enemyColors[k], Roughness = 0.9f } };

        Color[] itemColors = { Palette.Wood, Palette.Stone, Palette.Wheat, Palette.Moss };
        _itemMeshes = new Mesh[4];
        for (int k = 0; k < 4; k++)
            _itemMeshes[k] = new BoxMesh { Size = new Vector3(0.24f, 0.24f, 0.24f), Material = new StandardMaterial3D { AlbedoColor = itemColors[k], Roughness = 0.9f } };

        _machineBody = new BoxMesh { Size = new Vector3(0.7f, 0.5f, 0.7f), Material = new StandardMaterial3D { AlbedoColor = Palette.Stone, Roughness = 0.9f } };
        _machineRoof = new PrismMesh { Size = new Vector3(0.84f, 0.38f, 0.84f), Material = new StandardMaterial3D { AlbedoColor = Palette.Wood, Roughness = 0.9f } };
    }

    // ---- Modo nós -------------------------------------------------------------------------------------

    private void BuildNodes()
    {
        _nodesRoot = new Node3D { Name = "Nodes" };
        AddChild(_nodesRoot);
        _enemyNodes = new MeshInstance3D[_world.EnemyCount];
        for (int i = 0; i < _world.EnemyCount; i++)
        {
            _enemyNodes[i] = new MeshInstance3D { Mesh = _enemyMeshes[_world.EnemyKind[i]] };
            _nodesRoot.AddChild(_enemyNodes[i]);
        }
        _itemNodes = new MeshInstance3D[_world.ItemCount];
        for (int i = 0; i < _world.ItemCount; i++)
        {
            _itemNodes[i] = new MeshInstance3D { Mesh = _itemMeshes[_world.ItemKind[i]] };
            _nodesRoot.AddChild(_itemNodes[i]);
        }
        for (int i = 0; i < _world.MachineCount; i++)
        {
            var at = new Vector3(_world.MachineX[i], 0f, _world.MachineZ[i]);
            _nodesRoot.AddChild(new MeshInstance3D { Mesh = _machineBody, Position = at + Vector3.Up * 0.25f });
            _nodesRoot.AddChild(new MeshInstance3D { Mesh = _machineRoof, Position = at + Vector3.Up * 0.69f });
        }
    }

    private void RenderNodes(float alpha)
    {
        for (int i = 0; i < _world.EnemyCount; i++)
        {
            float x = Mathf.Lerp(_world.EnemyPrevX[i], _world.EnemyX[i], alpha);
            float z = Mathf.Lerp(_world.EnemyPrevZ[i], _world.EnemyZ[i], alpha);
            _enemyNodes[i].Position = new Vector3(x, 0.4f, z);
            _enemyNodes[i].Rotation = new Vector3(0f, _world.EnemyYaw[i], 0f);
        }
        for (int i = 0; i < _world.ItemCount; i++)
        {
            float x = Mathf.Lerp(_world.ItemPrevX[i], _world.ItemX[i], alpha);
            float z = Mathf.Lerp(_world.ItemPrevZ[i], _world.ItemZ[i], alpha);
            _itemNodes[i].Position = new Vector3(x, 0.22f, z);
        }
    }

    // ---- Modo MultiMesh -------------------------------------------------------------------------------

    private void BuildMultiMeshes()
    {
        _multiRoot = new Node3D { Name = "MultiMeshes" };
        AddChild(_multiRoot);
        _chunksX = (FieldWidth + ChunkCells - 1) / ChunkCells;
        _chunksZ = (FieldHeight + ChunkCells - 1) / ChunkCells;

        _enemySets = new ChunkSet[_enemyMeshes.Length];
        for (int k = 0; k < _enemyMeshes.Length; k++)
            _enemySets[k] = NewChunkSet($"Enemy{k}", _enemyMeshes[k], 1.2f);
        _itemSets = new ChunkSet[_itemMeshes.Length];
        for (int k = 0; k < _itemMeshes.Length; k++)
            _itemSets[k] = NewChunkSet($"Item{k}", _itemMeshes[k], 0.5f);

        // Máquinas não se mexem: buffers escritos uma vez.
        ChunkSet body = NewChunkSet("MachineBody", _machineBody, 1f), roof = NewChunkSet("MachineRoof", _machineRoof, 1.2f);
        BeginFrame(body); BeginFrame(roof);
        for (int i = 0; i < _world.MachineCount; i++)
        {
            Push(body, _world.MachineX[i], 0.25f, _world.MachineZ[i], 0f);
            Push(roof, _world.MachineX[i], 0.69f, _world.MachineZ[i], 0f);
        }
        EndFrame(body); EndFrame(roof);
    }

    private ChunkSet NewChunkSet(string name, Mesh mesh, float height)
    {
        int n = _chunksX * _chunksZ;
        var set = new ChunkSet
        {
            Nodes = new MultiMeshInstance3D[n], Buffers = new float[n][], Counts = new int[n],
            MinX = new float[n], MaxX = new float[n], MinZ = new float[n], MaxZ = new float[n], Height = height,
        };
        for (int c = 0; c < n; c++)
        {
            int cx = c % _chunksX, cz = c / _chunksX;
            var node = new MultiMeshInstance3D
            {
                Name = $"{name}_{cx}_{cz}",
                Multimesh = new MultiMesh { TransformFormat = MultiMesh.TransformFormatEnum.Transform3D, Mesh = mesh, InstanceCount = 0 },
                // Caixa fixa do pedaço: o culling por pedaço funciona sem recalcular a caixa a cada quadro.
                CustomAabb = new Aabb(new Vector3(cx * ChunkCells - 1f, -0.5f, cz * ChunkCells - 1f), new Vector3(ChunkCells + 2f, height + 1f, ChunkCells + 2f)),
            };
            _multiRoot.AddChild(node);
            set.Nodes[c] = node;
            set.Buffers[c] = Array.Empty<float>();
        }
        return set;
    }

    private static void BeginFrame(ChunkSet set)
    {
        Array.Clear(set.Counts);
        Array.Fill(set.MinX, float.MaxValue); Array.Fill(set.MinZ, float.MaxValue);
        Array.Fill(set.MaxX, float.MinValue); Array.Fill(set.MaxZ, float.MinValue);
    }

    /// <summary>Escreve uma transformação (giro em Y + posição) no buffer do pedaço da posição.</summary>
    private void Push(ChunkSet set, float x, float y, float z, float yaw)
    {
        int cx = Math.Clamp((int)(x / ChunkCells), 0, _chunksX - 1), cz = Math.Clamp((int)(z / ChunkCells), 0, _chunksZ - 1);
        int c = cz * _chunksX + cx;
        int i = set.Counts[c]++;
        if (x < set.MinX[c]) set.MinX[c] = x;
        if (x > set.MaxX[c]) set.MaxX[c] = x;
        if (z < set.MinZ[c]) set.MinZ[c] = z;
        if (z > set.MaxZ[c]) set.MaxZ[c] = z;
        float[] buffer = set.Buffers[c];
        if ((i + 1) * 12 > buffer.Length)
        {
            int capacity = Math.Max(64, buffer.Length / 12 * 2);
            Array.Resize(ref buffer, capacity * 12);
            set.Buffers[c] = buffer;
        }
        float cos = MathF.Cos(yaw), sin = MathF.Sin(yaw);
        int o = i * 12;
        // Linhas da matriz 3×4: (eixo X, eixo Y, eixo Z, origem) por componente.
        buffer[o + 0] = cos;  buffer[o + 1] = 0f; buffer[o + 2] = sin;  buffer[o + 3] = x;
        buffer[o + 4] = 0f;   buffer[o + 5] = 1f; buffer[o + 6] = 0f;   buffer[o + 7] = y;
        buffer[o + 8] = -sin; buffer[o + 9] = 0f; buffer[o + 10] = cos; buffer[o + 11] = z;
    }

    /// <summary>Manda os buffers para a GPU; o MultiMesh só cresce (nunca realoca para menos).</summary>
    private static void EndFrame(ChunkSet set)
    {
        for (int c = 0; c < set.Nodes.Length; c++)
        {
            int count = set.Counts[c];
            MultiMesh mm = set.Nodes[c].Multimesh;
            if (count == 0)
            {
                mm.VisibleInstanceCount = 0;
                continue;
            }
            int capacity = set.Buffers[c].Length / 12;
            if (mm.InstanceCount != capacity)
                mm.InstanceCount = capacity;
            mm.Buffer = set.Buffers[c];
            mm.VisibleInstanceCount = count;
            set.Nodes[c].CustomAabb = new Aabb(new Vector3(set.MinX[c] - 0.6f, -0.1f, set.MinZ[c] - 0.6f),
                new Vector3(set.MaxX[c] - set.MinX[c] + 1.2f, set.Height + 0.6f, set.MaxZ[c] - set.MinZ[c] + 1.2f));
        }
    }

    private void RenderMultiMeshes(float alpha)
    {
        foreach (ChunkSet set in _enemySets) BeginFrame(set);
        foreach (ChunkSet set in _itemSets) BeginFrame(set);
        for (int i = 0; i < _world.EnemyCount; i++)
        {
            float x = Mathf.Lerp(_world.EnemyPrevX[i], _world.EnemyX[i], alpha);
            float z = Mathf.Lerp(_world.EnemyPrevZ[i], _world.EnemyZ[i], alpha);
            Push(_enemySets[_world.EnemyKind[i]], x, 0.4f, z, _world.EnemyYaw[i]);
        }
        for (int i = 0; i < _world.ItemCount; i++)
        {
            float x = Mathf.Lerp(_world.ItemPrevX[i], _world.ItemX[i], alpha);
            float z = Mathf.Lerp(_world.ItemPrevZ[i], _world.ItemZ[i], alpha);
            Push(_itemSets[_world.ItemKind[i]], x, 0.22f, z, 0f);
        }
        foreach (ChunkSet set in _enemySets) EndFrame(set);
        foreach (ChunkSet set in _itemSets) EndFrame(set);
    }

    // ---- Laço ------------------------------------------------------------------------------------------

    public override void _Process(double delta)
    {
        long t0 = System.Diagnostics.Stopwatch.GetTimestamp();
        int ticks = _clock.Advance(delta);
        for (int i = 0; i < ticks; i++)
            _world.Tick();
        long t1 = System.Diagnostics.Stopwatch.GetTimestamp();

        float alpha = (float)_clock.Alpha;
        if (_mode == Mode.Nodes) RenderNodes(alpha);
        else RenderMultiMeshes(alpha);
        RenderVillagers((float)delta);
        long t2 = System.Diagnostics.Stopwatch.GetTimestamp();

        // Média móvel curta, para o painel não tremer.
        _simMs = Mathf.Lerp(_simMs, System.Diagnostics.Stopwatch.GetElapsedTime(t0, t1).TotalMilliseconds, 0.1);
        _viewMs = Mathf.Lerp(_viewMs, System.Diagnostics.Stopwatch.GetElapsedTime(t1, t2).TotalMilliseconds, 0.1);

        MoveCamera((float)delta);
        _accum += delta;
        if (_accum >= 0.25)
        {
            _accum = 0;
            UpdateLabel();
        }
    }

    private void ApplyMode()
    {
        _nodesRoot.Visible = _mode == Mode.Nodes;
        _multiRoot.Visible = _mode == Mode.MultiMesh;
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is InputEventKey { Pressed: true, Echo: false } key)
        {
            switch (key.PhysicalKeycode)
            {
                case Key.M: _mode = _mode == Mode.Nodes ? Mode.MultiMesh : Mode.Nodes; ApplyMode(); break;
                case Key.G: if (_grass is not null) _grass.Visible = !_grass.Visible; break;
                case Key.Key0: SetVillagerCount(0); break;
                case Key.Key1: SetVillagerCount(50); break;
                case Key.Key2: SetVillagerCount(200); break;
                case Key.Key3: SetVillagerCount(500); break;
                case Key.H:
                    // Esconde inimigos, itens e máquinas: mede só os aldeões sobre o campo.
                    _nodesRoot.Visible = !_nodesRoot.Visible && _mode == Mode.Nodes;
                    _multiRoot.Visible = !_multiRoot.Visible && _mode == Mode.MultiMesh;
                    break;
                case Key.F2:
                    DisplayServer.WindowSetVsyncMode(DisplayServer.WindowGetVsyncMode() == DisplayServer.VSyncMode.Disabled
                        ? DisplayServer.VSyncMode.Enabled : DisplayServer.VSyncMode.Disabled);
                    break;
                case Key.F3: _label.Visible = !_label.Visible; break;
                case Key.F11:
                    string path = ProjectSettings.GlobalizePath($"res://docs/prints/estresse_{Time.GetTicksMsec()}.png");
                    GetViewport().GetTexture().GetImage().SavePng(path);
                    GD.Print($"[estresse] captura salva em {path}");
                    break;
            }
        }
        if (@event is InputEventMouseButton { Pressed: true } wheel)
        {
            if (wheel.ButtonIndex == MouseButton.WheelUp) _distance = Mathf.Max(6f, _distance / 1.1f);
            if (wheel.ButtonIndex == MouseButton.WheelDown) _distance = Mathf.Min(120f, _distance * 1.1f);
            PlaceCamera();
        }
    }

    private void MoveCamera(float dt)
    {
        var dir = Vector3.Zero;
        if (Input.IsPhysicalKeyPressed(Key.W)) dir.Z -= 1f;
        if (Input.IsPhysicalKeyPressed(Key.S)) dir.Z += 1f;
        if (Input.IsPhysicalKeyPressed(Key.A)) dir.X -= 1f;
        if (Input.IsPhysicalKeyPressed(Key.D)) dir.X += 1f;
        if (dir == Vector3.Zero)
            return;
        _lookAt += dir.Normalized() * dt * _distance * 0.6f;
        PlaceCamera();
    }

    private void PlaceCamera()
    {
        float pitch = Mathf.DegToRad(Pitch);
        var offset = new Vector3(0f, Mathf.Sin(pitch), Mathf.Cos(pitch)) * _distance;
        _camera.Position = _lookAt + offset;
        _camera.LookAt(_lookAt, Vector3.Up);
    }

    private void UpdateLabel()
    {
        double fps = Engine.GetFramesPerSecond();
        double frameMs = fps > 0 ? 1000.0 / fps : 0;
        var sb = new StringBuilder();
        if (!GetWindow().HasFocus())
            sb.AppendLine("[JANELA SEM FOCO: medição inválida]");
        sb.AppendLine($"TESTE DE ESTRESSE  |  modo: {(_mode == Mode.Nodes ? "um nó por entidade" : "MultiMesh por tipo e pedaço")}  (M troca)");
        sb.AppendLine($"{fps:0} FPS  quadro {frameMs:0.0} ms  |  simulação {_simMs:0.00} ms  |  view {_viewMs:0.00} ms  |  tick {_world.TickCount}");
        sb.AppendLine($"inimigos {_world.EnemyCount}  máquinas {_world.MachineCount}  itens {_world.ItemCount}  (horda {(_nodesRoot.Visible || _multiRoot.Visible ? "visível" : "oculta")})  " +
            $"aldeões animados {_villagerVisuals.Count}  campo {FieldWidth}×{FieldHeight}  grama {(_grass is null ? "não" : _grass.Visible ? $"{_grass.TuftCount} tufos" : "oculta")}");
        sb.AppendLine($"draw calls {Performance.GetMonitor(Performance.Monitor.RenderTotalDrawCallsInFrame):0}  |  objetos {Performance.GetMonitor(Performance.Monitor.RenderTotalObjectsInFrame):0}  |  " +
            $"nós {Performance.GetMonitor(Performance.Monitor.ObjectNodeCount):0}  |  VRAM {Performance.GetMonitor(Performance.Monitor.RenderVideoMemUsed) / 1048576.0:0} MB  |  " +
            $"tela {DisplayServer.WindowGetSize().X}x{DisplayServer.WindowGetSize().Y}  distância {_distance:0}  V-Sync {(DisplayServer.WindowGetVsyncMode() == DisplayServer.VSyncMode.Disabled ? "off" : "on")}");
        sb.Append("M modo  G grama  H horda  0/1/2/3 aldeões 0/50/200/500  F2 V-Sync  F3 painel  F11 captura  roda aproxima  WASD anda");
        _label.Text = sb.ToString();
    }
}
