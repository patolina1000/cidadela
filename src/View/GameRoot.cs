using System.Linq;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Liga a simulação à cena: carrega os dados e o mapa, transforma a entrada do jogador
/// em comandos, avança o <see cref="SimClock"/> a cada frame, roda os ticks e pede para a
/// <see cref="WorldView"/> desenhar.
/// </summary>
public partial class GameRoot : Node3D
{
    [Export(PropertyHint.File, "*.json")] public string MapPath = "res://data/maps/mapa_teste.json";
    [Export(PropertyHint.File, "*.json")] public string ResourcesPath = "res://data/resources.json";
    [Export(PropertyHint.File, "*.json")] public string CastellanPath = "res://data/castellan.json";

    private SimWorld _world = null!;
    private readonly SimClock _clock = new();
    private WorldView _view = null!;
    private CameraRig _camera = null!;
    private Label _debugLabel = null!;
    private Label _inventoryLabel = null!;

    private System.Numerics.Vector2 _lastMoveSent;
    private long _ticksAtLastSample;
    private double _sampleTime;
    private int _measuredTicksPerSecond;

    public override void _Ready()
    {
        GameData data = GameData.Parse(
            FileAccess.GetFileAsString(ResourcesPath),
            FileAccess.GetFileAsString(CastellanPath));
        _world = MapLoader.Parse(FileAccess.GetFileAsString(MapPath), data);

        _view = GetNode<WorldView>("WorldView");
        _view.Build(_world);

        _camera = GetNode<CameraRig>("CameraRig");
        _camera.Target = _view.CastellanNode;
        _camera.SetBounds(new Rect2(0f, 0f, _world.Grid.Width, _world.Grid.Height));

        _debugLabel = GetNode<Label>("DebugHud/DebugLabel");
        _inventoryLabel = GetNode<Label>("DebugHud/InventoryLabel");
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        // Clique esquerdo: coletar o recurso da célula (a simulação confere se está encostado e se há recurso).
        if (@event is InputEventMouseButton { ButtonIndex: MouseButton.Left, Pressed: true } click
            && CellUnder(click.Position) is GridPos cell)
        {
            _world.Enqueue(new GatherCommand(cell));
        }
    }

    public override void _Process(double delta)
    {
        SendMoveInput();

        int ticks = _clock.Advance(delta);
        for (int i = 0; i < ticks; i++)
            _world.Tick();

        _view.Render(_clock.Alpha, delta);
        _view.ShowHover(_camera.Cursor is Vector2 cursor ? CellUnder(cursor) : null);
        UpdateHud(delta);
    }

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
        string gathering = castellan.GatherTarget is ResourceNode node
            ? $"   |   Coletando {node.Type.Name} {castellan.GatherProgress:P0} (restam {node.Remaining})"
            : "";
        _inventoryLabel.Text = items + gathering;
    }
}
