using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Menu inicial (scenes/Menu.tscn): o crepúsculo do jogo ao fundo, com a protagonista parada em idle e o
/// cristal aceso, sobre um pedaço de grama (aguardando o novo aldeão: os aldeões em volta dela voltam com ele).
/// Botões: Novo jogo, Continuar
/// (desativado sem save), Biografia, Configurações (<see cref="SettingsPanel"/>) e Sair.
/// </summary>
public partial class MenuRoot : Node3D
{
    private const int FieldSize = 24;

    private GameData _data = null!;
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

        _camera = new Camera3D { Name = "Camera", Fov = 38f, Current = true };
        AddChild(_camera);
        // O painel do menu cobre o terço esquerdo: o grupo fica à direita do centro da tela.
        _camera.Position = center + new Vector3(0.4f, 1.05f, 3.8f);
        _camera.LookAt(center + new Vector3(-0.35f, 0.55f, 0f), Vector3.Up);
    }

    public override void _Process(double delta)
    {
        _time += (float)delta;
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

        VBoxContainer column = MenuStyle.AddLeftPanel(layer);
        MenuStyle.AddTitle(column, "protótipo, crepúsculo eterno");

        MenuStyle.AddButton(column, "Novo jogo", () => GetTree().ChangeSceneToFile(GameFiles.GameScene));
        Button resume = MenuStyle.AddButton(column, "Continuar", () => GetTree().ChangeSceneToFile(GameFiles.GameScene));
        resume.Disabled = !GameFiles.HasSave();
        resume.TooltipText = resume.Disabled ? "Nenhum jogo salvo." : "";
        MenuStyle.AddButton(column, "Biografia", () =>
        {
            if (ResourceLoader.Exists(GameFiles.BiographyScene))
                GetTree().ChangeSceneToFile(GameFiles.BiographyScene);
        });
        MenuStyle.AddButton(column, "Configurações", () => _settings.Visible = !_settings.Visible);
        MenuStyle.AddButton(column, "Sair", () => GetTree().Quit());

        var spacer = new Control { SizeFlagsVertical = Control.SizeFlags.ExpandFill };
        column.AddChild(spacer);
        var version = new Label { Text = "Godot 4.7.2 .NET  ·  build de desenvolvimento" };
        version.AddThemeFontSizeOverride("font_size", 12);
        version.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.4f));
        column.AddChild(version);

        _settings = new SettingsPanel();
        layer.AddChild(_settings);
    }
}
