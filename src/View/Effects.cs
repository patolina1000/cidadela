using Godot;

namespace Cidadela.View;

/// <summary>Efeitos curtos e descartáveis: lascas e texto flutuante. Só visuais.</summary>
public partial class Effects : Node3D
{
    /// <summary>Lascas pequenas da cor dada, saltando para cima e caindo.</summary>
    public void Burst(Vector3 position, Color color, int amount, float speed = 2.5f)
    {
        var chip = new BoxMesh { Size = new Vector3(0.09f, 0.09f, 0.09f) };
        chip.Material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.9f };

        var particles = new CpuParticles3D
        {
            Name = "Burst",
            Position = position,
            Mesh = chip,
            Amount = amount,
            Lifetime = 0.6,
            OneShot = true,
            Explosiveness = 1f,
            Direction = Vector3.Up,
            Spread = 55f,
            InitialVelocityMin = speed * 0.6f,
            InitialVelocityMax = speed,
            Gravity = new Vector3(0f, -9.8f, 0f),
            AngularVelocityMin = -360f,
            AngularVelocityMax = 360f,
            ScaleAmountMin = 0.6f,
            ScaleAmountMax = 1.3f,
            Emitting = true,
        };
        AddChild(particles);
        GetTree().CreateTimer(particles.Lifetime + 0.2).Timeout += particles.QueueFree;
    }

    /// <summary>Texto que sobe e some, sempre virado para a câmera e por cima de tudo.</summary>
    public void FloatingText(Vector3 position, string text, Color color)
    {
        var label = new Label3D
        {
            Text = text,
            Position = position,
            Billboard = BaseMaterial3D.BillboardModeEnum.Enabled,
            NoDepthTest = true,
            FontSize = 44,
            PixelSize = 0.006f,
            OutlineSize = 10,
            Modulate = color,
            OutlineModulate = new Color(0f, 0f, 0f, 0.8f),
        };
        AddChild(label);

        Tween tween = CreateTween().SetParallel();
        tween.TweenProperty(label, "position", position + new Vector3(0f, 1.1f, 0f), 0.9)
            .SetEase(Tween.EaseType.Out).SetTrans(Tween.TransitionType.Cubic);
        tween.TweenProperty(label, "modulate:a", 0f, 0.5).SetDelay(0.4);
        tween.TweenProperty(label, "outline_modulate:a", 0f, 0.5).SetDelay(0.4);
        tween.Chain().TweenCallback(Callable.From(label.QueueFree));
    }
}
