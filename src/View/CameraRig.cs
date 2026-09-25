using Godot;

namespace Cidadela.View;

/// <summary>
/// Câmera no estilo do Factorio (GDD, seções 12 e 20), em 3D inclinado:
/// travada no Castelão (sempre no centro, sem atraso), sem giro (norte sempre para cima),
/// inclinação fixa e só o zoom na roda do mouse.
/// O nó fica no chão, no ponto que a câmera olha; a câmera filha fica a uma distância e inclinação.
/// </summary>
public partial class CameraRig : Node3D
{
    /// <summary>Distância no zoom padrão (zoom 1).</summary>
    [Export] public float DefaultDistance = 16f;

    /// <summary>Zoom mínimo (mais afastado). Factorio: cerca de 0,4.</summary>
    [Export] public float MinZoom = 0.4f;

    /// <summary>Zoom máximo (mais perto).</summary>
    [Export] public float MaxZoom = 2.5f;

    /// <summary>Quanto cada clique da roda multiplica o zoom. Factorio: cerca de 1,1.</summary>
    [Export] public float ZoomStep = 1.1f;

    /// <summary>Inclinação fixa em graus acima do horizonte.</summary>
    [Export] public float Pitch = 55f;

    /// <summary>Quão rápido o zoom alcança o alvo (maior = mais rápido).</summary>
    [Export] public float ZoomSmoothing = 15f;

    /// <summary>O que a câmera segue.</summary>
    public Node3D? Target { get; set; }

    private Camera3D _camera = null!;
    private float _zoom = 1f;
    private float _targetZoom = 1f;

    public override void _Ready()
    {
        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        ApplyTransform();
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is not InputEventMouseButton { Pressed: true } mouse)
            return;

        if (mouse.ButtonIndex == MouseButton.WheelUp)
            _targetZoom = Mathf.Min(_targetZoom * ZoomStep, MaxZoom);
        else if (mouse.ButtonIndex == MouseButton.WheelDown)
            _targetZoom = Mathf.Max(_targetZoom / ZoomStep, MinZoom);
    }

    public override void _Process(double delta)
    {
        _zoom = Mathf.Lerp(_zoom, _targetZoom, 1f - Mathf.Exp(-ZoomSmoothing * (float)delta));

        // Travada: o desenho do Castelão já é interpolado entre ticks, então seguir sem atraso fica suave.
        if (Target is not null)
            Position = new Vector3(Target.GlobalPosition.X, 0f, Target.GlobalPosition.Z);

        ApplyTransform();
    }

    private void ApplyTransform()
    {
        float distance = DefaultDistance / _zoom;
        float pitch = Mathf.DegToRad(Pitch);
        _camera.Position = new Vector3(0f, Mathf.Sin(pitch) * distance, Mathf.Cos(pitch) * distance);
        _camera.Rotation = new Vector3(-pitch, 0f, 0f);
    }
}
