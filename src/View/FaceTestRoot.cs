using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Cena de teste do rosto (scenes/tests/FaceTest.tscn): um aldeão placeholder (esfera no lugar da cabeça, os
/// dois retalhos curvos e o atlas provisório gerado por código) de perto, percorrendo as 9 expressões do GDD
/// a cada <see cref="SecondsPerExpression"/> segundos e piscando pelo <see cref="FaceAnimator"/>. Os atlas
/// aparecem embaixo, para conferir qual célula está no rosto. Espaço pausa a troca; Esc volta ao menu.
/// </summary>
public partial class FaceTestRoot : Node3D
{
    private const float SecondsPerExpression = 1.5f;

    private VillagerVisual _visual = null!;
    private Label _label = null!;
    private float _time;
    private int _index;
    private bool _paused;

    public override void _Ready()
    {
        var ground = new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(6f, 6f), Material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f } },
        };
        AddChild(ground);

        var sun = new DirectionalLight3D { Name = "Sun", LightColor = new Color(0.72f, 0.78f, 0.9f), LightEnergy = 1.1f, ShadowEnabled = true };
        AddChild(sun);
        sun.Position = new Vector3(1f, 2f, -2f);
        sun.LookAt(new Vector3(0f, 0.3f, 0f), Vector3.Up);

        // O aldeão fica na célula (0, 0): o visual soma 0,5, então a posição de desenho é (-0,5, -0,5).
        _visual = new VillagerVisual { Name = "Villager", ForcePlaceholder = true, Seed = 1 };
        AddChild(_visual);

        var camera = new Camera3D { Name = "Camera", Fov = 28f, Current = true };
        AddChild(camera);
        camera.Position = new Vector3(0.12f, 0.42f, -0.62f);
        camera.LookAt(new Vector3(0f, 0.33f, 0f), Vector3.Up);

        var hud = new CanvasLayer { Name = "Hud" };
        AddChild(hud);
        _label = new Label { Position = new Vector2(16f, 12f) };
        _label.AddThemeFontSizeOverride("font_size", 26);
        _label.AddThemeColorOverride("font_color", Palette.Bone);
        _label.AddThemeColorOverride("font_outline_color", Colors.Black);
        _label.AddThemeConstantOverride("outline_size", 6);
        hud.AddChild(_label);

        // Os dois atlas provisórios, para conferir a célula escolhida.
        var eyes = new TextureRect { Texture = VillagerLooks.EyesAtlas(), Position = new Vector2(16f, 470f), Scale = new Vector2(0.55f, 0.55f) };
        var mouth = new TextureRect { Texture = VillagerLooks.MouthAtlas(), Position = new Vector2(190f, 470f), Scale = new Vector2(0.55f, 0.55f) };
        hud.AddChild(eyes);
        hud.AddChild(mouth);
        var caption = new Label { Text = "olhos.png (provisório)              boca.png (provisório)", Position = new Vector2(16f, 550f) };
        caption.AddThemeFontSizeOverride("font_size", 14);
        caption.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.7f));
        hud.AddChild(caption);
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is not InputEventKey { Pressed: true, Echo: false } key)
            return;
        if (key.PhysicalKeycode == Key.Space)
            _paused = !_paused;
        else if (key.PhysicalKeycode == Key.Escape)
            GetTree().ChangeSceneToFile(GameFiles.MenuScene);
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        if (!_paused)
        {
            _time += dt;
            if (_time >= SecondsPerExpression)
            {
                _time -= SecondsPerExpression;
                _index = (_index + 1) % VillagerExpressions.All.Length;
            }
        }
        VillagerExpression expression = VillagerExpressions.All[_index];
        var state = new VillagerVisual.DrawState(new System.Numerics.Vector2(-0.5f, -0.5f), new System.Numerics.Vector2(0f, -1f),
            1 + _index % Villager.HairVariants, expression, expression == VillagerExpression.Sleeping, null, null, -1f, 0f);
        _visual.UpdateFrom(state, null, dt);
        _label.Text = $"{_index + 1}/9  {VillagerExpressions.Name(expression)}{(_visual.IsBlinking ? "   (piscando)" : "")}\n" +
            "Espaço pausa a troca  ·  Esc volta ao menu";
    }
}
