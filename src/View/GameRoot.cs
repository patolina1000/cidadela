using System.Linq;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Liga a simulação à cena: carrega os dados e o mapa, transforma a entrada do jogador
/// em comandos, avança o <see cref="SimClock"/> a cada frame, roda os ticks e pede para a
/// <see cref="WorldView"/> desenhar.
/// Mouse: esquerdo coleta (ou constrói, com uma construção escolhida; segurar e arrastar faz fileira);
/// direito sem arrastar cancela a escolha ou desmonta. Teclado: WASD anda, 1–9 escolhem, R gira, Esc cancela.
/// </summary>
public partial class GameRoot : Node3D
{
    [Export(PropertyHint.File, "*.json")] public string MapPath = "res://data/maps/mapa_teste.json";
    [Export(PropertyHint.File, "*.json")] public string ResourcesPath = "res://data/resources.json";
    [Export(PropertyHint.File, "*.json")] public string CastellanPath = "res://data/castellan.json";
    [Export(PropertyHint.File, "*.json")] public string BuildingsPath = "res://data/buildings.json";

    private SimWorld _world = null!;
    private readonly SimClock _clock = new();
    private WorldView _view = null!;
    private CameraRig _camera = null!;
    private Hotbar _hotbar = null!;
    private Label _debugLabel = null!;
    private Label _inventoryLabel = null!;

    // Modo de construção: o que está escolhido, para onde aponta e a última célula do arrasto.
    private BuildingType? _selected;
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
            FileAccess.GetFileAsString(ResourcesPath),
            FileAccess.GetFileAsString(CastellanPath),
            FileAccess.GetFileAsString(BuildingsPath));
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
        else if (k == Key.Escape)
        {
            Select(null);
        }
    }

    /// <summary>Clique esquerdo numa célula: constrói (se há escolha) ou coleta. A simulação confere tudo.</summary>
    private void ActAt(GridPos cell)
    {
        if (_selected is not null)
        {
            _world.Enqueue(new BuildCommand(_selected.Kind, cell, _buildDirection));
            _lastBuildCell = cell;
        }
        else
        {
            _world.Enqueue(new GatherCommand(cell));
        }
    }

    private void OnRightClick(Vector2 screenPos)
    {
        if (_selected is not null)
            Select(null);
        else if (CellUnder(screenPos) is GridPos cell)
            _world.Enqueue(new DeconstructCommand(cell));
    }

    private void Select(int? index)
    {
        _selected = index is int i ? _world.Data.Buildings[i] : null;
        _hotbar.ShowSelected(index);
    }

    public override void _Process(double delta)
    {
        SendMoveInput();

        Vector2? cursor = CursorOverWorld();
        GridPos? hovered = cursor is Vector2 c ? CellUnder(c) : null;

        // Segurar o esquerdo e arrastar constrói uma fileira, uma célula de cada vez.
        if (_leftHeld && _selected is not null && hovered is GridPos cell && cell != _lastBuildCell)
            ActAt(cell);

        int ticks = _clock.Advance(delta);
        for (int i = 0; i < ticks; i++)
            _world.Tick();

        _view.Render(_clock.Alpha, delta);
        _view.ShowHover(_selected is null ? hovered : null);
        _view.ShowGhost(_selected, hovered, _buildDirection);
        _hotbar.ShowAffordable(_world.Castellan.Inventory);
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
            $"{Engine.GetFramesPerSecond()} FPS  |  Castelão ({p.X:0.0}, {p.Y:0.0})";

        string items = string.Join("   ", _world.Data.Resources.Values.Select(
            r => $"{r.Name}: {castellan.Inventory.Count(r.Kind)}"));
        string action = _selected is not null
            ? $"   |   Construindo {_selected.Name} ({DirectionName(_buildDirection)}) — R gira, botão direito cancela"
            : castellan.GatherTarget is ResourceNode node
                ? $"   |   Coletando {node.Type.Name} {castellan.GatherProgress:P0} (restam {node.Remaining})"
                : "";
        _inventoryLabel.Text = items + action;
    }

    private static string DirectionName(Direction d) => d switch
    {
        Direction.North => "norte",
        Direction.East => "leste",
        Direction.South => "sul",
        _ => "oeste",
    };
}
