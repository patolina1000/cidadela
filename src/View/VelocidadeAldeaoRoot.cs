using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Cena de comparação de velocidades do aldeão v2 (scenes/tests/VelocidadeAldeao.tscn): no crepúsculo do
/// jogo, quatro aldeões correm em círculos lado a lado, cada um numa velocidade (<see cref="Speeds"/>, em
/// células por segundo: a penalidade, a base e as duas melhorias de data/villagers.json); a reprodução do
/// clipe run acompanha a velocidade (velocidade ÷ passadaRun), então os pés nunca deslizam e o que muda é o
/// quanto a corrida parece acelerada. O rótulo sobre cada um
/// mostra velocidade e reprodução. A câmera fica no zoom padrão do jogo (55°, 16 unidades); a roda aproxima
/// e afasta como no jogo. Esc volta ao menu. Serve para o humano escolher a velocidade olhando, sem mudar
/// data/villagers.json.
/// </summary>
public partial class VelocidadeAldeaoRoot : Node3D
{
    private static readonly float[] Speeds = { 0.57f, 0.8f, 1.0f, 1.2f };
    private const int FieldSize = 28;
    private const float Radius = 1.5f, Spacing = 5f;
    private const float DefaultDistance = 16f, Pitch = 55f, MinZoom = 0.4f, MaxZoom = 2.5f, ZoomStep = 1.1f;

    private GameData _data = null!;
    private readonly List<VillagerVisual> _villagers = new();
    private readonly List<Vector3> _centers = new();
    private Camera3D _camera = null!;
    private Vector3 _lookAt;
    private float _zoom = 1f, _targetZoom = 1f, _time;

    public override void _Ready()
    {
        _data = GameFiles.LoadData();
        var grid = new WorldGrid(FieldSize, FieldSize); // tudo grama
        AddChild(new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(FieldSize, FieldSize), Material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f } },
            Position = new Vector3(FieldSize / 2f, 0f, FieldSize / 2f),
        });
        var grass = new GrassField { Name = "Grass" };
        AddChild(grass);
        grass.Build(grid, _data, _ => false);

        float stride = VillagerLooks.Face().StrideRun;
        _lookAt = new Vector3(FieldSize / 2f, 0f, FieldSize / 2f);
        for (int i = 0; i < Speeds.Length; i++)
        {
            var center = new Vector3(FieldSize / 2f + (i - (Speeds.Length - 1) / 2f) * Spacing, 0f, FieldSize / 2f);
            _centers.Add(center);
            var visual = new VillagerVisual { Name = $"Villager_{i}", Seed = i + 1 };
            AddChild(visual);
            _villagers.Add(visual);

            string speed = Speeds[i].ToString("0.00").Replace('.', ',');
            string playback = stride > 0f ? (Speeds[i] / stride).ToString("0.00").Replace('.', ',') : "?";
            AddChild(new Label3D
            {
                Name = $"Label_{i}",
                Text = $"{speed} células/s\n{playback}× o run",
                Position = center + new Vector3(0f, 1.1f, 0f),
                Billboard = BaseMaterial3D.BillboardModeEnum.Enabled,
                NoDepthTest = true,
                FontSize = 44,
                PixelSize = 0.006f,
                OutlineSize = 10,
                Modulate = Palette.Bone,
                OutlineModulate = new Color(0f, 0f, 0f, 0.8f),
                HorizontalAlignment = HorizontalAlignment.Center,
            });
        }

        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        PlaceCamera();

        var hud = new CanvasLayer { Name = "Hud" };
        AddChild(hud);
        var help = new Label { Text = "Comparação de velocidades do aldeão v2  ·  passadaRun " + stride.ToString("0.000").Replace('.', ',') + " m/s  ·  roda aproxima e afasta  ·  Esc volta ao menu", Position = new Vector2(16f, 12f) };
        help.AddThemeFontSizeOverride("font_size", 20);
        help.AddThemeColorOverride("font_color", Palette.Bone);
        help.AddThemeColorOverride("font_outline_color", Colors.Black);
        help.AddThemeConstantOverride("outline_size", 5);
        hud.AddChild(help);
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
            case InputEventKey { Pressed: true, Echo: false, PhysicalKeycode: Key.Escape }:
                GetTree().ChangeSceneToFile(GameFiles.MenuScene);
                break;
        }
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        _time += dt;
        for (int i = 0; i < _villagers.Count; i++)
        {
            // Círculo de raio fixo: a velocidade angular é velocidade ÷ raio; a frente é a tangente.
            float angle = _time * Speeds[i] / Radius;
            var offset = new System.Numerics.Vector2(Mathf.Cos(angle), Mathf.Sin(angle)) * Radius;
            var facing = new System.Numerics.Vector2(-Mathf.Sin(angle), Mathf.Cos(angle));
            var pos = new System.Numerics.Vector2(_centers[i].X - 0.5f + offset.X, _centers[i].Z - 0.5f + offset.Y);
            _villagers[i].UpdateFrom(new VillagerVisual.DrawState(pos, facing, 1 + i, VillagerExpression.Distracted, false, null, null, -1f, 0f), _data, dt);
        }
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
