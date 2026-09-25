using Godot;

namespace Cidadela.View;

/// <summary>
/// Câmera estilo Albion (GDD, seções 12 e 20) que segue o Castelão.
/// O nó fica no chão, no ponto que a câmera olha; o giro é o do próprio nó e a câmera
/// filha orbita a uma distância e inclinação. Tudo no mouse: roda dá zoom; segurar o
/// botão do meio e arrastar para os lados gira em passos de 90°.
/// </summary>
public partial class CameraRig : Node3D
{
    [Export] public float MinDistance = 6f;
    [Export] public float MaxDistance = 40f;
    [Export] public float StartDistance = 16f;
    [Export] public float ZoomStep = 0.85f;

    /// <summary>Inclinação em graus acima do horizonte: mais inclinada de perto, mais vertical de longe.</summary>
    [Export] public float PitchNear = 50f;
    [Export] public float PitchFar = 65f;

    /// <summary>Quantos pixels de arrasto com o botão do meio valem um passo de 90°.</summary>
    [Export] public float RotateDragPixels = 60f;

    /// <summary>Quão rápido zoom e giro alcançam o alvo (maior = mais rápido).</summary>
    [Export] public float Smoothing = 12f;

    /// <summary>Quão rápido a câmera alcança o Castelão; menor = atraso mais visível.</summary>
    [Export] public float FollowSmoothing = 8f;

    /// <summary>O que a câmera segue.</summary>
    public Node3D? Target { get; set; }

    /// <summary>Giro atual em radianos, para converter a entrada do jogador em direção no mundo.</summary>
    public float Yaw => _yaw;

    private Camera3D _camera = null!;
    private float _distance;
    private float _targetDistance;
    private float _yaw;
    private float _targetYaw;
    private bool _rotateDragging;
    private float _rotateDragAccum;
    private float _rotateDragLastX;

    public override void _Ready()
    {
        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        _distance = _targetDistance = StartDistance;
        _yaw = _targetYaw = Rotation.Y;
        ApplyTransform();
    }

    /// <summary>Pula direto para o alvo, sem suavizar (início de jogo, renascer).</summary>
    public void SnapToTarget()
    {
        if (Target is not null)
            Position = GroundPoint(Target);
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is InputEventMouseButton mouse)
        {
            if (mouse.ButtonIndex == MouseButton.Middle)
            {
                _rotateDragging = mouse.Pressed;
                _rotateDragAccum = 0f;
                _rotateDragLastX = mouse.Position.X;
            }
            else if (mouse.Pressed && mouse.ButtonIndex == MouseButton.WheelUp)
            {
                Zoom(ZoomStep);
            }
            else if (mouse.Pressed && mouse.ButtonIndex == MouseButton.WheelDown)
            {
                Zoom(1f / ZoomStep);
            }
        }
        else if (@event is InputEventMouseMotion motion && _rotateDragging)
        {
            // Como agarrar o mundo: arrastar para a direita gira o mundo para a direita.
            // Diferença de posição em vez de Relative: funciona também com eventos sintéticos.
            _rotateDragAccum += motion.Position.X - _rotateDragLastX;
            _rotateDragLastX = motion.Position.X;
            while (Mathf.Abs(_rotateDragAccum) >= RotateDragPixels)
            {
                float step = Mathf.Sign(_rotateDragAccum);
                _targetYaw -= step * Mathf.Pi / 2f;
                _rotateDragAccum -= step * RotateDragPixels;
            }
        }
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        float blend = 1f - Mathf.Exp(-Smoothing * dt);
        _distance = Mathf.Lerp(_distance, _targetDistance, blend);
        _yaw = Mathf.Lerp(_yaw, _targetYaw, blend);

        if (Target is not null)
        {
            float follow = 1f - Mathf.Exp(-FollowSmoothing * dt);
            Position = Position.Lerp(GroundPoint(Target), follow);
        }

        ApplyTransform();
    }

    private static Vector3 GroundPoint(Node3D target) =>
        new(target.GlobalPosition.X, 0f, target.GlobalPosition.Z);

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
