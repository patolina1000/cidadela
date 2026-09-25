using Godot;

namespace Cidadela.View;

/// <summary>
/// Câmera estilo Albion (GDD, seção 12). O nó fica no chão, no ponto que a câmera olha;
/// o giro é o do próprio nó e a câmera filha orbita a uma distância e inclinação.
/// WASD move, roda do mouse dá zoom, Q/E giram 90°.
/// </summary>
public partial class CameraRig : Node3D
{
    [Export] public float MinDistance = 6f;
    [Export] public float MaxDistance = 60f;
    [Export] public float StartDistance = 22f;
    [Export] public float ZoomStep = 0.85f;

    /// <summary>Inclinação em graus acima do horizonte: mais inclinada de perto, mais vertical de longe.</summary>
    [Export] public float PitchNear = 50f;
    [Export] public float PitchFar = 65f;

    /// <summary>Velocidade de movimento em telas por segundo, proporcional ao zoom.</summary>
    [Export] public float PanSpeed = 0.9f;

    /// <summary>Quão rápido zoom e giro alcançam o alvo (maior = mais rápido).</summary>
    [Export] public float Smoothing = 12f;

    private Camera3D _camera = null!;
    private float _distance;
    private float _targetDistance;
    private float _yaw;
    private float _targetYaw;
    private Rect2 _bounds = new(Vector2.Zero, new Vector2(float.MaxValue, float.MaxValue));

    public override void _Ready()
    {
        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        _distance = _targetDistance = StartDistance;
        _yaw = _targetYaw = Rotation.Y;
        ApplyTransform();
    }

    /// <summary>Limita o ponto focal a uma área do mapa (em X/Z).</summary>
    public void SetBounds(Rect2 bounds) => _bounds = bounds;

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is InputEventMouseButton { Pressed: true } mouse)
        {
            if (mouse.ButtonIndex == MouseButton.WheelUp)
                Zoom(ZoomStep);
            else if (mouse.ButtonIndex == MouseButton.WheelDown)
                Zoom(1f / ZoomStep);
        }
        else if (@event.IsActionPressed("camera_rotate_left"))
        {
            _targetYaw += Mathf.Pi / 2f;
        }
        else if (@event.IsActionPressed("camera_rotate_right"))
        {
            _targetYaw -= Mathf.Pi / 2f;
        }
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        float blend = 1f - Mathf.Exp(-Smoothing * dt);
        _distance = Mathf.Lerp(_distance, _targetDistance, blend);
        _yaw = Mathf.Lerp(_yaw, _targetYaw, blend);

        Vector2 input = Input.GetVector("camera_left", "camera_right", "camera_forward", "camera_back");
        if (input != Vector2.Zero)
        {
            // Direção relativa à câmera: "frente" é para onde ela olha, projetado no chão.
            Vector3 move = new Vector3(input.X, 0f, input.Y).Rotated(Vector3.Up, _yaw);
            Position += move * PanSpeed * _distance * dt;
        }

        Position = new Vector3(
            Mathf.Clamp(Position.X, _bounds.Position.X, _bounds.End.X),
            0f,
            Mathf.Clamp(Position.Z, _bounds.Position.Y, _bounds.End.Y));

        ApplyTransform();
    }

    private void Zoom(float factor)
    {
        _targetDistance = Mathf.Clamp(_targetDistance * factor, MinDistance, MaxDistance);
    }

    private void ApplyTransform()
    {
        Rotation = new Vector3(0f, _yaw, 0f);
        float t = Mathf.InverseLerp(MinDistance, MaxDistance, _distance);
        float pitch = Mathf.DegToRad(Mathf.Lerp(PitchNear, PitchFar, t));
        _camera.Position = new Vector3(0f, Mathf.Sin(pitch) * _distance, Mathf.Cos(pitch) * _distance);
        _camera.Rotation = new Vector3(-pitch, 0f, 0f);
    }
}
