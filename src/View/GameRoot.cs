using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Liga a simulação à cena: carrega o mapa, avança o <see cref="SimClock"/> a cada frame,
/// roda os ticks e pede para a <see cref="WorldView"/> desenhar.
/// </summary>
public partial class GameRoot : Node3D
{
    [Export(PropertyHint.File, "*.json")] public string MapPath = "res://data/maps/mapa_teste.json";

    private SimWorld _world = null!;
    private readonly SimClock _clock = new();
    private WorldView _view = null!;
    private Label _debugLabel = null!;

    private long _ticksAtLastSample;
    private double _sampleTime;
    private int _measuredTicksPerSecond;

    public override void _Ready()
    {
        _world = MapLoader.Parse(FileAccess.GetFileAsString(MapPath));

        _view = GetNode<WorldView>("WorldView");
        _view.Build(_world);

        var camera = GetNode<CameraRig>("CameraRig");
        var size = new Vector2(_world.Grid.Width, _world.Grid.Height);
        camera.SetBounds(new Rect2(Vector2.Zero, size));
        camera.Position = new Vector3(size.X / 2f, 0f, size.Y / 2f);

        _debugLabel = GetNode<Label>("DebugHud/DebugLabel");
    }

    public override void _Process(double delta)
    {
        int ticks = _clock.Advance(delta);
        for (int i = 0; i < ticks; i++)
            _world.Tick();

        _view.Render(_clock.Alpha);
        UpdateDebug(delta);
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
        _debugLabel.Text =
            $"Tick {_world.TickCount}  |  {_measuredTicksPerSecond} ticks/s (alvo {SimClock.TicksPerSecond})  |  {Engine.GetFramesPerSecond()} FPS";
    }
}
