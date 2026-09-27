using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Menu inicial (scenes/Menu.tscn): o crepúsculo do jogo ao fundo, com a protagonista parada em idle, o
/// cristal aceso e alguns aldeões por perto, sobre um pedaço de grama. Botões: Novo jogo, Continuar
/// (desativado sem save), Biografia, Configurações (esboço) e Sair.
/// </summary>
public partial class MenuRoot : Node3D
{
    private const int FieldSize = 24;

    private static readonly (float x, float z, int hair, VillagerExpression face, string? job)[] Villagers =
    {
        (-0.7f, 0.9f, 1, VillagerExpression.Distracted, null),
        (1.4f, 0.3f, 2, VillagerExpression.Sleepy, "wood"),
        (0.4f, 1.5f, 3, VillagerExpression.Happy, null),
        (1.7f, 1.3f, 5, VillagerExpression.Distracted, "stone"),
    };

    private GameData _data = null!;
    private readonly List<VillagerVisual> _villagers = new();
    private Camera3D _camera = null!;
    private Control _settings = null!;
    private float _time;

    public override void _Ready()
    {
        _data = GameFiles.LoadData();
        BuildBackdrop();
        BuildUi();
    }

    private void BuildBackdrop()
    {
        var grid = new WorldGrid(FieldSize, FieldSize); // tudo grama (terreno 0)
        var ground = new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(FieldSize, FieldSize), Material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f } },
            Position = new Vector3(FieldSize / 2f, 0f, FieldSize / 2f),
        };
        AddChild(ground);
        var grass = new GrassField { Name = "Grass" };
        AddChild(grass);
        grass.Build(grid, _data, _ => false);

        // Protagonista no centro do campo, de frente para a câmera (o visual olha para -Z; a câmera fica em +Z).
        var center = new Vector3(FieldSize / 2f, 0f, FieldSize / 2f);
        var castellan = new CastellanVisual { Name = "Castellan", Position = center, Rotation = new Vector3(0f, Mathf.Pi, 0f) };
        AddChild(castellan);

        foreach ((float x, float z, int hair, VillagerExpression face, string? job) in Villagers)
        {
            var visual = new VillagerVisual { Name = $"Villager_{_villagers.Count}" };
            AddChild(visual);
            _villagers.Add(visual);
            // Posição em coordenadas de célula (o VillagerVisual soma 0,5); virados mais ou menos para a câmera.
            var pos = new System.Numerics.Vector2(center.X - 0.5f + x, center.Z - 0.5f + z);
            var facing = System.Numerics.Vector2.Normalize(new System.Numerics.Vector2(-x * 0.3f, -1f));
            visual.SetMeta("state", new Godot.Collections.Array { pos.X, pos.Y, facing.X, facing.Y, hair, (int)face, job ?? "" });
        }

        _camera = new Camera3D { Name = "Camera", Fov = 38f, Current = true };
        AddChild(_camera);
        // O painel do menu cobre o terço esquerdo: o grupo fica à direita do centro da tela.
        _camera.Position = center + new Vector3(0.4f, 1.05f, 3.8f);
        _camera.LookAt(center + new Vector3(-0.35f, 0.55f, 0f), Vector3.Up);
    }

    public override void _Process(double delta)
    {
        _time += (float)delta;
        for (int i = 0; i < _villagers.Count; i++)
        {
            var s = _villagers[i].GetMeta("state").AsGodotArray();
            var state = new VillagerVisual.DrawState(
                new System.Numerics.Vector2(s[0].AsSingle(), s[1].AsSingle()),
                new System.Numerics.Vector2(s[2].AsSingle(), s[3].AsSingle()),
                s[4].AsInt32(), (VillagerExpression)s[5].AsInt32(), false, null,
                string.IsNullOrEmpty(s[6].AsString()) ? null : s[6].AsString(), -1f, 0f);
            _villagers[i].UpdateFrom(state, _data, (float)delta);
        }
        // Balanço lento da câmera, como uma respiração.
        _camera.Position += new Vector3(0f, Mathf.Sin(_time * 0.4f) * 0.0004f, 0f);
    }

    private void BuildUi()
    {
        var layer = new CanvasLayer { Name = "Ui" };
        AddChild(layer);

        var vignette = new ColorRect { Name = "Vignette", Material = GD.Load<ShaderMaterial>("res://scenes/vignette_material.tres"), MouseFilter = Control.MouseFilterEnum.Ignore };
        vignette.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        layer.AddChild(vignette);

        var panel = new PanelContainer { Name = "Panel" };
        panel.AnchorTop = 0f; panel.AnchorBottom = 1f; panel.AnchorLeft = 0f; panel.AnchorRight = 0f;
        panel.OffsetLeft = 0f; panel.OffsetRight = 400f;
        panel.AddThemeStyleboxOverride("panel", new StyleBoxFlat
        {
            BgColor = new Color(0.06f, 0.05f, 0.09f, 0.72f),
            ContentMarginLeft = 44, ContentMarginRight = 44, ContentMarginTop = 60, ContentMarginBottom = 40,
        });
        layer.AddChild(panel);

        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 10);
        panel.AddChild(column);

        var title = new Label { Text = "Engrenagens da\nCidadela" };
        title.AddThemeFontSizeOverride("font_size", 40);
        title.AddThemeColorOverride("font_color", Palette.Bone);
        column.AddChild(title);
        var subtitle = new Label { Text = "protótipo, crepúsculo eterno" };
        subtitle.AddThemeFontSizeOverride("font_size", 15);
        subtitle.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.55f));
        column.AddChild(subtitle);
        column.AddChild(new Control { CustomMinimumSize = new Vector2(0, 30) });

        AddButton(column, "Novo jogo", () => GetTree().ChangeSceneToFile(GameFiles.GameScene));
        Button resume = AddButton(column, "Continuar", () => GetTree().ChangeSceneToFile(GameFiles.GameScene));
        resume.Disabled = !GameFiles.HasSave();
        resume.TooltipText = resume.Disabled ? "Nenhum jogo salvo." : "";
        AddButton(column, "Biografia", () =>
        {
            if (ResourceLoader.Exists(GameFiles.BiographyScene))
                GetTree().ChangeSceneToFile(GameFiles.BiographyScene);
        });
        AddButton(column, "Configurações", () => _settings.Visible = !_settings.Visible);
        AddButton(column, "Sair", () => GetTree().Quit());

        var spacer = new Control { SizeFlagsVertical = Control.SizeFlags.ExpandFill };
        column.AddChild(spacer);
        var version = new Label { Text = "Godot 4.7.2 .NET  ·  build de desenvolvimento" };
        version.AddThemeFontSizeOverride("font_size", 12);
        version.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.4f));
        column.AddChild(version);

        _settings = BuildSettings();
        layer.AddChild(_settings);
    }

    private static Button AddButton(Control parent, string text, System.Action onPressed)
    {
        var button = new Button { Text = text, Alignment = HorizontalAlignment.Left, CustomMinimumSize = new Vector2(0, 46) };
        button.AddThemeFontSizeOverride("font_size", 22);
        button.AddThemeColorOverride("font_color", Palette.Bone);
        button.AddThemeColorOverride("font_hover_color", Colors.White);
        button.AddThemeColorOverride("font_disabled_color", new Color(Palette.Bone, 0.3f));
        var normal = new StyleBoxFlat { BgColor = new Color(0, 0, 0, 0), ContentMarginLeft = 14 };
        var hover = new StyleBoxFlat { BgColor = new Color(Palette.PurpleLichen, 0.35f), ContentMarginLeft = 14, CornerRadiusTopLeft = 4, CornerRadiusTopRight = 4, CornerRadiusBottomLeft = 4, CornerRadiusBottomRight = 4 };
        button.AddThemeStyleboxOverride("normal", normal);
        button.AddThemeStyleboxOverride("disabled", normal);
        button.AddThemeStyleboxOverride("hover", hover);
        button.AddThemeStyleboxOverride("pressed", hover);
        button.AddThemeStyleboxOverride("focus", new StyleBoxEmpty());
        button.Pressed += onPressed;
        parent.AddChild(button);
        return button;
    }

    /// <summary>Esboço das configurações: tela cheia e V-Sync funcionam; volume ainda não tem som para controlar.</summary>
    private Control BuildSettings()
    {
        var box = new PanelContainer { Name = "Settings", Visible = false };
        box.AnchorLeft = 0f; box.AnchorRight = 0f; box.AnchorTop = 0.5f; box.AnchorBottom = 0.5f;
        box.OffsetLeft = 420f; box.OffsetRight = 800f; box.OffsetTop = -120f; box.OffsetBottom = 120f;
        box.AddThemeStyleboxOverride("panel", new StyleBoxFlat
        {
            BgColor = new Color(0.06f, 0.05f, 0.09f, 0.85f), BorderColor = new Color(Palette.PurpleLichen, 0.6f),
            BorderWidthLeft = 1, BorderWidthTop = 1, BorderWidthRight = 1, BorderWidthBottom = 1,
            ContentMarginLeft = 24, ContentMarginRight = 24, ContentMarginTop = 18, ContentMarginBottom = 18,
        });
        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 10);
        box.AddChild(column);

        var title = new Label { Text = "Configurações (esboço)" };
        title.AddThemeFontSizeOverride("font_size", 20);
        title.AddThemeColorOverride("font_color", Palette.Bone);
        column.AddChild(title);

        var fullscreen = new CheckBox { Text = "Tela cheia", ButtonPressed = DisplayServer.WindowGetMode() == DisplayServer.WindowMode.Fullscreen };
        fullscreen.Toggled += on => DisplayServer.WindowSetMode(on ? DisplayServer.WindowMode.Fullscreen : DisplayServer.WindowMode.Windowed);
        column.AddChild(fullscreen);

        var vsync = new CheckBox { Text = "V-Sync", ButtonPressed = DisplayServer.WindowGetVsyncMode() != DisplayServer.VSyncMode.Disabled };
        vsync.Toggled += on => DisplayServer.WindowSetVsyncMode(on ? DisplayServer.VSyncMode.Enabled : DisplayServer.VSyncMode.Disabled);
        column.AddChild(vsync);

        column.AddChild(new Label { Text = "Volume (ainda sem som)" });
        column.AddChild(new HSlider { MinValue = 0, MaxValue = 100, Value = 80, Editable = false });

        var close = new Button { Text = "Fechar" };
        close.Pressed += () => box.Visible = false;
        column.AddChild(close);
        return box;
    }
}
