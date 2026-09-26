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

    /// <summary>
    /// Um cubinho que voa em arco de <paramref name="from"/> até o alvo (seguindo o alvo se ele andar)
    /// e some ao chegar. Mostra itens voltando para o Castelão.
    /// </summary>
    public void FlyTo(Vector3 from, Node3D target, Color color, double delay)
    {
        var cube = new BoxMesh { Size = new Vector3(0.14f, 0.14f, 0.14f) };
        cube.Material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.9f };
        var node = new MeshInstance3D { Mesh = cube, Position = from, Visible = false };
        node.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        AddChild(node);

        Tween tween = CreateTween();
        tween.TweenInterval(delay);
        tween.TweenCallback(Callable.From(() => node.Visible = true));
        tween.TweenMethod(Callable.From<float>(t =>
        {
            Vector3 to = target.GlobalPosition + new Vector3(0f, 0.9f, 0f);
            Vector3 mid = (from + to) / 2f + new Vector3(0f, 1.3f, 0f);
            // Curva de Bézier quadrática: sobe, faz a volta e desce no Castelão.
            node.Position = from.Lerp(mid, t).Lerp(mid.Lerp(to, t), t);
            node.Rotation = new Vector3(t * 9f, t * 7f, 0f);
            node.Scale = Vector3.One * (1f - 0.6f * t * t);
        }), 0f, 1f, 0.5).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.In);
        tween.TweenCallback(Callable.From(node.QueueFree));
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
