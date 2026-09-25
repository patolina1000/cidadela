using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Liga a simulação à cena: carrega o mapa, transforma o WASD em comandos,
/// avança o <see cref="SimClock"/> a cada frame, roda os ticks e pede para a
/// <see cref="WorldView"/> desenhar.
/// </summary>
public partial class GameRoot : Node3D
{
    [Export(PropertyHint.File, "*.json")] public string MapPath = "res://data/maps/mapa_teste.json";

    private SimWorld _world = null!;
    private readonly SimClock _clock = new();
    private WorldView _view = null!;
    private Label _debugLabel = null!;

    private System.Numerics.Vector2 _lastMoveSent;
    private long _ticksAtLastSample;
    private double _sampleTime;
    private int _measuredTicksPerSecond;

    public override void _Ready()
    {
        _world = MapLoader.Parse(FileAccess.GetFileAsString(MapPath));

        _view = GetNode<WorldView>("WorldView");
        _view.Build(_world);

        GetNode<CameraRig>("CameraRig").Target = _view.CastellanNode;

        _debugLabel = GetNode<Label>("DebugHud/DebugLabel");
    }

    public override void _Process(double delta)
    {
        SendMoveInput();

        int ticks = _clock.Advance(delta);
        for (int i = 0; i < ticks; i++)
            _world.Tick();

        _view.Render(_clock.Alpha);
        UpdateDebug(delta);
    }

    /// <summary>
    /// A câmera não gira, então W é sempre o norte (-Z) do mundo.
    /// Só manda comando quando a direção muda, para não encher a fila.
    /// </summary>
    private void SendMoveInput()
    {
        Vector2 input = Input.GetVector("move_left", "move_right", "move_forward", "move_back");
        var direction = new System.Numerics.Vector2(input.X, input.Y);

        if (direction == _lastMoveSent)
            return;
        _world.Enqueue(new MoveCommand(direction));
        _lastMoveSent = direction;
    }

    private void UpdateDebug(double delta)
    {
        _sampleTime += delta;
        if (_sampleTime >= 1.0)
        {
            _measuredTicksPerSecond = (int)(_world.TickCount - _ticksAtLastSample);
            _ticksAtLastSample = _world.TickCount;
            _sampleTime -= 1.0;
        }
        System.Numerics.Vector2 p = _world.Castellan.Position;
        _debugLabel.Text =
            $"Tick {_world.TickCount}  |  {_measuredTicksPerSecond} ticks/s (alvo {SimClock.TicksPerSecond})  |  " +
            $"{Engine.GetFramesPerSecond()} FPS  |  Castelão ({p.X:0.0}, {p.Y:0.0})";
    }
}
