using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Liga a simulação à cena: carrega os dados e o mapa, transforma a entrada do jogador
/// em comandos, avança o <see cref="SimClock"/> a cada frame, roda os ticks e pede para a
/// <see cref="WorldView"/> desenhar.
/// WASD move o Castelão (ela só corre; não há andar nem botão de correr).
/// Mouse: esquerdo coleta, recolhe de um baú, constrói (com uma construção escolhida) ou põe o item da mão
/// numa esteira ou baú (com um item segurado); segurar e arrastar repete célula a célula.
/// Direito sem arrastar solta o que está escolhido ou desmonta. Teclado: WASD anda, 1–9 escolhem, R gira, Esc solta,
/// C entra/sai da câmera cinematográfica no que está sob o cursor (ou no Castelão).
/// </summary>
public partial class GameRoot : Node3D
{
    [Export(PropertyHint.File, "*.json")] public string MapPath = "res://data/maps/aldeoes_teste.json";
    [Export(PropertyHint.File, "*.json")] public string ItemsPath = "res://data/items.json";
    [Export(PropertyHint.File, "*.json")] public string ResourcesPath = "res://data/resources.json";
    [Export(PropertyHint.File, "*.json")] public string CastellanPath = "res://data/castellan.json";
    [Export(PropertyHint.File, "*.json")] public string VillagersPath = "res://data/villagers.json";
    [Export(PropertyHint.File, "*.json")] public string BuildingsPath = "res://data/buildings.json";
    [Export(PropertyHint.File, "*.json")] public string RecipesPath = "res://data/recipes.json";
    [Export(PropertyHint.File, "*.json")] public string TerrainPath = "res://data/terrain.json";

    private SimWorld _world = null!;
    private readonly SimClock _clock = new();
    private WorldView _view = null!;
    private CameraRig _camera = null!;
    private Hotbar _hotbar = null!;
    private InventoryBar _inventoryBar = null!;
    private CinematicOverlay _cinematicOverlay = null!;
    private FocusTarget? _focus;
    private Label _debugLabel = null!;
    private PerfOverlay _perf = null!;
    private Label _inventoryLabel = null!;

    // Modo de construção: o que está escolhido, para onde aponta e a última célula do arrasto.
    private BuildingType? _selected;
    private string? _heldItem;
    private Direction _buildDirection = Direction.North;
    private bool _leftHeld;
    private GridPos? _lastBuildCell;

    private System.Numerics.Vector2 _lastMoveSent;
    private long _ticksAtLastSample;
    private double _sampleTime;
    private int _measuredTicksPerSecond;

    public override void _Ready()
    {
        GameData data = GameData.Parse(
            FileAccess.GetFileAsString(ItemsPath),
            FileAccess.GetFileAsString(ResourcesPath),
            FileAccess.GetFileAsString(CastellanPath),
            FileAccess.GetFileAsString(VillagersPath),
            FileAccess.GetFileAsString(BuildingsPath),
            FileAccess.GetFileAsString(RecipesPath),
            FileAccess.GetFileAsString(TerrainPath));
        _world = MapLoader.Parse(FileAccess.GetFileAsString(MapPath), data);

        _view = GetNode<WorldView>("WorldView");
        _view.Build(_world);

        _camera = GetNode<CameraRig>("CameraRig");
        _camera.Target = _view.CastellanNode;
        _camera.SetBounds(new Rect2(0f, 0f, _world.Grid.Width, _world.Grid.Height));
        _camera.RightClicked += OnRightClick;

        _debugLabel = GetNode<Label>("DebugHud/DebugLabel");
        _inventoryLabel = GetNode<Label>("DebugHud/InventoryLabel");

        _hotbar = new Hotbar { Name = "Hotbar" };
        GetNode("DebugHud").AddChild(_hotbar);
        _hotbar.Build(data.Buildings, data);
        _hotbar.SlotClicked += Select;

        _inventoryBar = new InventoryBar { Name = "InventoryBar" };
        GetNode("DebugHud").AddChild(_inventoryBar);
        _inventoryBar.Build(data.Items);
        _inventoryBar.ItemClicked += Hold;

        _cinematicOverlay = new CinematicOverlay { Name = "CinematicOverlay" };
        GetNode("DebugHud").AddChild(_cinematicOverlay);

        _perf = new PerfOverlay { Name = "PerfOverlay" };
        GetNode("DebugHud").AddChild(_perf);
        _perf.Setup(_view, GetNode<WorldEnvironment>("WorldEnvironment"), GetNode<DirectionalLight3D>("Sun"),
            GetNode<CanvasItem>("DebugHud/Vignette"));

        // A linha de status desce para baixo dos botões do inventário.
        _inventoryLabel.OffsetTop = 72f;
        _inventoryLabel.OffsetBottom = 98f;
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is InputEventKey { Pressed: true, Echo: false } key)
            HandleKey(key);

        if (@event is InputEventMouseButton { ButtonIndex: MouseButton.Left } click)
        {
            _leftHeld = click.Pressed;
            _lastBuildCell = null;
            if (click.Pressed && CellUnder(click.Position) is GridPos cell)
                ActAt(cell);
        }
    }

    private void HandleKey(InputEventKey key)
    {
        Key k = key.PhysicalKeycode;
        if (_perf.HandleKey(k))
            return;
        if (k >= Key.Key1 && k <= Key.Key9)
        {
            int index = (int)(k - Key.Key1);
            if (index < _world.Data.Buildings.Count)
                Select(_selected == _world.Data.Buildings[index] ? null : index); // mesma tecla desmarca
        }
        else if (k == Key.R && _selected is not null)
        {
            _buildDirection = _buildDirection.RotatedClockwise();
        }
        else if (k == Key.C)
        {
            ToggleCinematic();
        }
        else if (k == Key.Escape)
        {
            if (_camera.IsCinematic)
            {
                ToggleCinematic();
                return;
            }
            Select(null);
            Hold(null);
        }
    }

    /// <summary>
    /// Entra na câmera cinematográfica no que está sob o cursor (Castelão, aldeão, construção, recurso;
    /// sem nada, o Castelão) ou sai dela. Solta o que estava escolhido para não construir sem querer.
    /// </summary>
    private void ToggleCinematic()
    {
        if (_camera.IsCinematic)
        {
            _camera.ExitCinematic();
            return;
        }
        Select(null);
        Hold(null);
        Vector3? ground = CursorOverWorld() is Vector2 cursor ? _camera.GroundUnder(cursor) : null;
        _focus = (ground is Vector3 g ? _view.FindFocus(g) : null) ?? _view.CastellanFocus();
        _camera.EnterCinematic(_focus.Node, _focus.Height, _focus.Distance);
    }

    /// <summary>
    /// Clique esquerdo numa célula: constrói, põe o item da mão, recolhe de um baú ou coleta.
    /// A simulação confere tudo (alcance, itens, espaço).
    /// </summary>
    private void ActAt(GridPos cell)
    {
        _lastBuildCell = cell;
        if (_selected is not null)
            _world.Enqueue(new BuildCommand(_selected.Kind, cell, _buildDirection));
        else if (_heldItem is not null)
            _world.Enqueue(new InsertItemCommand(cell, _heldItem));
        else if (_world.BuildingAt(cell) is { } b && (b.Storage is not null || b.Machine is not null || b.Workplace is not null))
            _world.Enqueue(new TakeAllCommand(cell));
        else
            _world.Enqueue(new GatherCommand(cell));
    }

    private void OnRightClick(Vector2 screenPos)
    {
        if (_selected is not null || _heldItem is not null)
        {
            Select(null);
            Hold(null);
        }
        else if (CellUnder(screenPos) is GridPos cell)
        {
            _world.Enqueue(new DeconstructCommand(cell));
        }
    }

    /// <summary>Escolhe uma construção da barra (ou nenhuma). Solta o item da mão.</summary>
    private void Select(int? index)
    {
        _selected = index is int i ? _world.Data.Buildings[i] : null;
        _hotbar.ShowSelected(index);
        if (_selected is not null)
            Hold(null);
    }

    /// <summary>Segura um item do inventário na mão (ou nenhum). Desmarca a construção.</summary>
    private void Hold(string? kind)
    {
        _heldItem = kind;
        _inventoryBar.ShowHeld(kind);
        if (kind is not null)
        {
            _selected = null;
            _hotbar.ShowSelected(null);
        }
    }

    public override void _Process(double delta)
    {
        long started = System.Diagnostics.Stopwatch.GetTimestamp();
        SendMoveInput();

        Vector2? cursor = CursorOverWorld();
        GridPos? hovered = cursor is Vector2 c ? CellUnder(c) : null;

        // Segurar o esquerdo e arrastar repete a ação célula a célula (fileira de esteiras, itens em várias).
        if (_leftHeld && (_selected is not null || _heldItem is not null) && hovered is GridPos cell && cell != _lastBuildCell)
            ActAt(cell);

        int ticks = _clock.Advance(delta);
        for (int i = 0; i < ticks; i++)
            _world.Tick();

        _view.Render(_clock.Alpha, delta);
        _perf.GameCpuMs = System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds;

        // Na cinematográfica, a interface some e só ficam as faixas com a legenda ao vivo.
        bool cinematic = _camera.IsCinematic;
        if (cinematic && _focus is not null)
            _cinematicOverlay.SetCaption(_focus.Describe() + "     (C ou Esc sai)");
        _cinematicOverlay.Show(cinematic);
        _hotbar.Visible = !cinematic;
        _inventoryBar.Visible = !cinematic;
        _inventoryLabel.Visible = !cinematic;
        _debugLabel.Visible = !cinematic;
        if (cinematic)
            hovered = null;

        _view.ShowHover(_selected is null ? hovered : null);
        _view.ShowGhost(_selected, hovered, _buildDirection);
        _view.ShowBuildingInfo(hovered);
        _hotbar.ShowAffordable(_world.Castellan.Inventory);
        _inventoryBar.ShowCounts(_world.Castellan.Inventory);
        UpdateHud(delta);
    }

    /// <summary>Cursor sobre o mundo; null se saiu da janela ou está em cima da barra.</summary>
    private Vector2? CursorOverWorld() =>
        GetViewport().GuiGetHoveredControl() is null ? _camera.Cursor : null;

    /// <summary>
    /// WASD é relativo à câmera; a simulação quer direção no mundo.
    /// Só manda comando quando a direção muda, para não encher a fila.
    /// </summary>
    private void SendMoveInput()
    {
        Vector2 input = Input.GetVector("move_left", "move_right", "move_forward", "move_back");
        Vector3 world = new Vector3(input.X, 0f, input.Y).Rotated(Vector3.Up, _camera.Yaw);
        var direction = new System.Numerics.Vector2(world.X, world.Z);

        // Andar traz a câmera solta de volta para o Castelão.
        if (direction != System.Numerics.Vector2.Zero)
            _camera.ReturnToTarget();

        if (direction == _lastMoveSent)
            return;
        _world.Enqueue(new MoveCommand(direction));
        _lastMoveSent = direction;
    }

    /// <summary>Célula do chão sob uma posição da tela. A célula x ocupa [x, x+1] no mundo.</summary>
    private GridPos? CellUnder(Vector2 screenPos) =>
        _camera.GroundUnder(screenPos) is Vector3 p
            ? new GridPos(Mathf.FloorToInt(p.X), Mathf.FloorToInt(p.Z))
            : null;

    private void UpdateHud(double delta)
    {
        _sampleTime += delta;
        if (_sampleTime >= 1.0)
        {
            _measuredTicksPerSecond = (int)(_world.TickCount - _ticksAtLastSample);
            _ticksAtLastSample = _world.TickCount;
            _sampleTime -= 1.0;
        }
        Castellan castellan = _world.Castellan;
        System.Numerics.Vector2 p = castellan.Position;
        _debugLabel.Text =
            $"Tick {_world.TickCount}  |  {_measuredTicksPerSecond} ticks/s (alvo {SimClock.TicksPerSecond})  |  " +
            $"{Engine.GetFramesPerSecond()} FPS  |  Castelão ({p.X:0.0}, {p.Y:0.0})  |  grama: {_view.GrassTufts} tufos";

        _inventoryLabel.Text = _selected is not null
            ? $"Construindo {_selected.Name} ({DirectionName(_buildDirection)}) — R gira, botão direito cancela"
            : _heldItem is not null
                ? $"Segurando {_world.Data.Item(_heldItem).Name} — clique numa esteira, baú ou máquina; botão direito solta"
                : castellan.GatherTarget is ResourceNode node
                    ? $"Coletando {node.Type.Name} {castellan.GatherProgress:P0} (restam {node.Remaining})"
                    : "";
    }

    private static string DirectionName(Direction d) => d switch
    {
        Direction.North => "norte",
        Direction.East => "leste",
        Direction.South => "sul",
        _ => "oeste",
    };
}
