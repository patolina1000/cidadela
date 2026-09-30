using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Cena de comparação (scenes/tests/ProtagonistaV2.tscn): no crepúsculo do jogo, a protagonista v1, a v2 e um aldeão v2
/// lado a lado, parados no lugar, de frente para a câmera. Espaço alterna idle e corrida (no lugar, em 1×); a roda
/// aproxima e afasta como no jogo (câmera a 55°, 16 unidades no zoom 1, até 2,5); Esc volta ao menu.
/// </summary>
public partial class ProtagonistaV2Root : Node3D
{
    private const int FieldSize = 16;
    private const float Spacing = 1.6f;
    private const float DefaultDistance = 16f, Pitch = 55f, MinZoom = 0.4f, MaxZoom = 2.5f, ZoomStep = 1.1f;

    private GameData _data = null!;
    private CastellanVisual _v1 = null!, _v2 = null!;
    private VillagerVisual _villager = null!;
    private Vector3 _lookAt, _villagerAt;
    private Camera3D _camera = null!;
    private Label _help = null!;
    private bool _running;
    private float _zoom = 2.5f, _targetZoom = 2.5f;

    public override void _Ready()
    {
        _data = GameFiles.LoadData();
        var grid = new WorldGrid(FieldSize, FieldSize);
        AddChild(new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(FieldSize, FieldSize), Material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f } },
            Position = new Vector3(FieldSize / 2f, 0f, FieldSize / 2f),
        });
        var grass = new GrassField { Name = "Grass" };
        AddChild(grass);
        grass.Build(grid, _data, _ => false);

        _lookAt = new Vector3(FieldSize / 2f, 0.3f, FieldSize / 2f);
        // O visual do Castelão olha para -Z; a câmera fica em +Z: gira 180° para ficar de frente.
        _v1 = new CastellanVisual { Name = "V1", UseV1 = true, Position = _lookAt with { Y = 0f } + new Vector3(-Spacing, 0f, 0f), Rotation = new Vector3(0f, Mathf.Pi, 0f) };
        _v2 = new CastellanVisual { Name = "V2", Position = _lookAt with { Y = 0f }, Rotation = new Vector3(0f, Mathf.Pi, 0f) };
        AddChild(_v1);
        AddChild(_v2);
        _villager = new VillagerVisual { Name = "Aldeao", Seed = 3 };
        AddChild(_villager);
        _villagerAt = _lookAt with { Y = 0f } + new Vector3(Spacing, 0f, 0f);
        Label(_v1.Position, "v1");
        Label(_v2.Position, "v2");
        Label(_villagerAt, "aldeão v2");

        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        PlaceCamera();

        var hud = new CanvasLayer { Name = "Hud" };
        AddChild(hud);
        _help = new Label { Position = new Vector2(16f, 12f) };
        _help.AddThemeFontSizeOverride("font_size", 20);
        _help.AddThemeColorOverride("font_color", Palette.Bone);
        _help.AddThemeColorOverride("font_outline_color", Colors.Black);
        _help.AddThemeConstantOverride("outline_size", 5);
        hud.AddChild(_help);
        Apply();
    }

    private void Label(Vector3 at, string text) => AddChild(new Label3D
    {
        Text = text,
        Position = at + new Vector3(0f, 1.05f, 0f),
        Billboard = BaseMaterial3D.BillboardModeEnum.Enabled,
        NoDepthTest = true,
        FontSize = 40,
        PixelSize = 0.004f,
        OutlineSize = 10,
        Modulate = Palette.Bone,
        OutlineModulate = new Color(0f, 0f, 0f, 0.8f),
    });

    private void Apply()
    {
        string clip = _running ? "run" : "idle";
        _v1.PlayClip(clip);
        _v2.PlayClip(clip);
        _villager.PreviewClip = clip;
        _help.Text = $"Protagonista v1 × v2 × aldeão v2  ·  {(_running ? "corrida" : "idle")} (Espaço alterna)  ·  roda aproxima e afasta  ·  Esc volta ao menu";
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        switch (@event)
        {
            case InputEventKey { Pressed: true, Echo: false, PhysicalKeycode: Key.Space }:
                _running = !_running;
                Apply();
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelUp }:
                _targetZoom = Mathf.Min(_targetZoom * ZoomStep, MaxZoom);
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelDown }:
                _targetZoom = Mathf.Max(_targetZoom / ZoomStep, MinZoom);
                break;
            case InputEventKey { Pressed: true, Echo: false, PhysicalKeycode: Key.Escape }:
                GetTree().ChangeSceneToFile(GameFiles.MenuScene);
                break;
        }
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        var pos = new System.Numerics.Vector2(_villagerAt.X - 0.5f, _villagerAt.Z - 0.5f);
        _villager.UpdateFrom(new VillagerVisual.DrawState(pos, new System.Numerics.Vector2(0f, 1f), 1, VillagerExpression.Distracted,
            false, null, null, -1f, 0f), _data, dt);
        _zoom = Mathf.Lerp(_zoom, _targetZoom, 1f - Mathf.Exp(-8f * dt));
        PlaceCamera();
    }

    private void PlaceCamera()
    {
        float pitch = Mathf.DegToRad(Pitch);
        var offset = new Vector3(0f, Mathf.Sin(pitch), Mathf.Cos(pitch)) * (DefaultDistance / _zoom);
        _camera.Position = _lookAt + offset;
        _camera.LookAt(_lookAt, Vector3.Up);
    }
}
