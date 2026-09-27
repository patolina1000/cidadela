using System;
using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Biografia (scenes/Biography.tscn): a enciclopédia do jogo. Colunas: categorias, entradas da categoria,
/// palco 3D no centro com a iluminação do jogo, texto à direita. No palco, arrastar com o botão esquerdo
/// gira e a roda aproxima. Embaixo, botões de animação da entrada (clipes dos personagens; funcionando e
/// parada nas máquinas) e, no aldeão, expressões e cabelos. Tudo vem de data/biography.json.
/// </summary>
public partial class BiographyRoot : Node3D
{
    private const int FieldSize = 16;
    private const float LeftWidth = 230f, ListWidth = 250f, RightWidth = 380f, BottomHeight = 246f;

    private GameData _data = null!;
    private List<Biography.Category> _categories = new();
    private List<Biography.Entry> _entries = new();
    private Biography.Entry? _current;

    private Node3D _stage = null!;
    private Node3D? _model;
    private CastellanVisual? _castellan;
    private VillagerVisual? _villager;
    private VillagerVisual.DrawState _villagerState;
    private Camera3D _camera = null!;
    private float _yaw = Mathf.Pi, _pitch = 0.32f, _distance = 3f, _targetHeight = 0.4f;
    private bool _dragging;
    private Vector2 _lastMouse;
    private float _spin;
    private bool _machineRunning = true;

    private VBoxContainer _entryList = null!;
    private Label _title = null!, _description = null!, _story = null!;
    private VBoxContainer _controls = null!;
    private readonly List<Button> _categoryButtons = new();

    public override void _Ready()
    {
        _data = GameFiles.LoadData();
        (_categories, _entries) = Biography.Load();
        BuildStage();
        BuildUi();
        if (_categories.Count > 0)
            ShowCategory(_categories[0]);
    }

    // ---- Palco --------------------------------------------------------------------------------------------

    private void BuildStage()
    {
        var grid = new WorldGrid(FieldSize, FieldSize);
        var center = new Vector3(FieldSize / 2f, 0f, FieldSize / 2f);
        AddChild(new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(FieldSize, FieldSize), Material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f } },
            Position = center,
        });
        // Um pátio de terra no meio (sem grama) para o modelo, grama em volta.
        var grass = new GrassField { Name = "Grass" };
        AddChild(grass);
        grass.Build(grid, _data, cell => Math.Abs(cell.X - FieldSize / 2) <= 1 && Math.Abs(cell.Z - FieldSize / 2) <= 1);
        AddChild(new MeshInstance3D
        {
            Name = "Pedestal",
            Mesh = new CylinderMesh { TopRadius = 1.4f, BottomRadius = 1.5f, Height = 0.04f, Material = new StandardMaterial3D { AlbedoColor = Palette.DeepPurple.Lightened(0.08f), Roughness = 0.95f } },
            Position = center + new Vector3(0f, 0.02f, 0f),
        });

        _stage = new Node3D { Name = "Stage", Position = center + new Vector3(0f, 0.04f, 0f) };
        AddChild(_stage);
        _camera = new Camera3D { Name = "Camera", Fov = 40f, Current = true };
        AddChild(_camera);
        PlaceCamera();
    }

    private void PlaceCamera()
    {
        Vector3 target = _stage.GlobalPosition + new Vector3(0f, _targetHeight, 0f);
        var offset = new Vector3(Mathf.Sin(_yaw) * Mathf.Cos(_pitch), Mathf.Sin(_pitch), Mathf.Cos(_yaw) * Mathf.Cos(_pitch)) * _distance;
        _camera.Position = target + offset;
        _camera.LookAt(target, Vector3.Up);
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        switch (@event)
        {
            case InputEventMouseButton { ButtonIndex: MouseButton.Left } click:
                _dragging = click.Pressed;
                _lastMouse = click.Position;
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelUp }:
                _distance = Mathf.Max(0.8f, _distance / 1.12f);
                PlaceCamera();
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelDown }:
                _distance = Mathf.Min(12f, _distance * 1.12f);
                PlaceCamera();
                break;
            case InputEventMouseMotion motion when _dragging:
                // Delta pela posição absoluta: eventos sintéticos (testes) podem vir sem Relative.
                Vector2 d = motion.Position - _lastMouse;
                _lastMouse = motion.Position;
                _yaw -= d.X * 0.006f;
                _pitch = Mathf.Clamp(_pitch + d.Y * 0.004f, -0.1f, 1.3f);
                PlaceCamera();
                break;
            case InputEventKey { Pressed: true, Echo: false, PhysicalKeycode: Key.Escape }:
                GetTree().ChangeSceneToFile(GameFiles.MenuScene);
                break;
        }
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        if (_villager is not null)
            _villager.UpdateFrom(_villagerState, _data, dt);
        // Itens e recursos giram devagar no palco; máquinas paradas ficam paradas.
        if (_model is not null && _current is { ModelKind: "item" or "resource" })
        {
            _spin += dt * 0.6f;
            _model.Rotation = new Vector3(0f, _spin, 0f);
        }
        if (_model is not null && _current is { ModelKind: "building" } && _model.GetNodeOrNull<Node3D>("Model") is Node3D machine)
        {
            if (machine.GetNodeOrNull<Node3D>("Spin") is Node3D spin && _machineRunning)
                spin.Rotation = new Vector3(spin.Rotation.X + dt * 12f, 0f, 0f);
            machine.Scale = _machineRunning && _current.Animations.Count > 0 ? new Vector3(1f, 1f + 0.04f * Mathf.Sin(_spin * 10f), 1f) : Vector3.One;
            _spin += dt;
        }
    }

    /// <summary>Monta no palco o modelo da entrada e reposiciona a câmera para o tamanho dele.</summary>
    private void ShowModel(Biography.Entry entry)
    {
        _model?.QueueFree();
        _model = null;
        _castellan = null;
        _villager = null;
        _spin = 0f;
        _machineRunning = true;

        switch (entry.ModelKind)
        {
            case "castellan":
                _castellan = new CastellanVisual { Name = "Castellan" };
                _model = _castellan;
                _targetHeight = 0.42f; _distance = 2.4f;
                break;
            case "villager":
                _villager = new VillagerVisual { Name = "Villager" };
                _villagerState = new VillagerVisual.DrawState(new System.Numerics.Vector2(-0.5f, -0.5f), new System.Numerics.Vector2(0f, -1f), // olha para -Z, onde a câmera começa
                    1, VillagerExpression.Distracted, false, null, null, -1f, 0f);
                _model = _villager;
                _targetHeight = 0.22f; _distance = 1.4f;
                break;
            case "building":
                BuildingType type = _data.Building(entry.ModelArg);
                _model = BuildingModels.Create(type, Direction.North, _data);
                _targetHeight = type.IsBelt ? 0.1f : 0.45f; _distance = type.IsBelt ? 2f : 3f;
                break;
            case "item":
            {
                var mesh = new BoxMesh { Size = new Vector3(0.24f, 0.24f, 0.24f), Material = new StandardMaterial3D { AlbedoColor = Palette.ForItem(_data, entry.ModelArg), Roughness = 0.9f } };
                _model = new Node3D();
                _model.AddChild(new MeshInstance3D { Mesh = mesh, Position = new Vector3(0f, 0.3f, 0f) });
                _targetHeight = 0.3f; _distance = 1.3f;
                break;
            }
            case "resource":
            {
                var mesh = new BoxMesh { Size = new Vector3(0.8f, 0.8f, 0.8f), Material = new StandardMaterial3D { AlbedoColor = Palette.ForItem(_data, entry.ModelArg), Roughness = 0.9f } };
                _model = new Node3D();
                _model.AddChild(new MeshInstance3D { Mesh = mesh, Position = new Vector3(0f, 0.4f, 0f) });
                _targetHeight = 0.4f; _distance = 2.6f;
                break;
            }
        }
        if (_model is not null)
            _stage.AddChild(_model);
        _yaw = Mathf.Pi;
        _pitch = 0.32f;
        PlaceCamera();
    }

    // ---- Interface ----------------------------------------------------------------------------------------

    private void BuildUi()
    {
        var layer = new CanvasLayer { Name = "Ui" };
        AddChild(layer);
        var vignette = new ColorRect { Name = "Vignette", Material = GD.Load<ShaderMaterial>("res://scenes/vignette_material.tres"), MouseFilter = Control.MouseFilterEnum.Ignore };
        vignette.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        layer.AddChild(vignette);

        // Categorias (esquerda).
        PanelContainer left = Panel(layer, 0f, 0f, 0f, 1f, 0f, LeftWidth, 0f, 0f);
        var leftColumn = new VBoxContainer();
        leftColumn.AddThemeConstantOverride("separation", 6);
        left.AddChild(leftColumn);
        leftColumn.AddChild(Heading("Biografia", 30));
        leftColumn.AddChild(new Control { CustomMinimumSize = new Vector2(0, 10) });
        foreach (Biography.Category category in _categories)
        {
            Biography.Category c = category;
            Button b = MenuButton(category.Name, 19, () => ShowCategory(c));
            leftColumn.AddChild(b);
            _categoryButtons.Add(b);
        }
        leftColumn.AddChild(new Control { SizeFlagsVertical = Control.SizeFlags.ExpandFill });
        leftColumn.AddChild(MenuButton("← Voltar ao menu", 16, () => GetTree().ChangeSceneToFile(GameFiles.MenuScene)));

        // Entradas (segunda coluna).
        PanelContainer list = Panel(layer, 0f, 0f, 0f, 1f, LeftWidth, LeftWidth + ListWidth, 0f, 0f, 0.55f);
        var scroll = new ScrollContainer { HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled };
        list.AddChild(scroll);
        _entryList = new VBoxContainer { SizeFlagsHorizontal = Control.SizeFlags.ExpandFill };
        _entryList.AddThemeConstantOverride("separation", 4);
        scroll.AddChild(_entryList);

        // Texto (direita).
        PanelContainer right = Panel(layer, 1f, 0f, 1f, 1f, -RightWidth, 0f, 0f, 0f);
        var rightColumn = new VBoxContainer();
        rightColumn.AddThemeConstantOverride("separation", 12);
        right.AddChild(rightColumn);
        _title = Heading("", 30);
        rightColumn.AddChild(_title);
        _description = Paragraph(17, new Color(Palette.Bone, 0.9f));
        rightColumn.AddChild(_description);
        rightColumn.AddChild(new HSeparator());
        _story = Paragraph(15, new Color(Palette.Bone, 0.72f));
        rightColumn.AddChild(_story);

        // Controles do palco (embaixo, no vão entre as colunas).
        PanelContainer bottom = Panel(layer, 0f, 1f, 1f, 1f, LeftWidth, -RightWidth, -BottomHeight, 0f, 0.6f);
        _controls = new VBoxContainer();
        _controls.AddThemeConstantOverride("separation", 6);
        bottom.AddChild(_controls);
    }

    private void ShowCategory(Biography.Category category)
    {
        for (int i = 0; i < _categories.Count; i++)
            _categoryButtons[i].AddThemeColorOverride("font_color", _categories[i] == category ? Colors.White : new Color(Palette.Bone, 0.7f));
        foreach (Node child in _entryList.GetChildren())
            child.QueueFree();

        Biography.Entry? first = null;
        foreach (Biography.Entry entry in _entries)
        {
            if (entry.CategoryId != category.Id)
                continue;
            first ??= entry;
            Biography.Entry e = entry;
            Button b = MenuButton(entry.Discovered ? entry.Name : "???", 17, () => ShowEntry(e));
            b.Disabled = !entry.Discovered;
            _entryList.AddChild(b);
        }
        if (first is null)
        {
            _entryList.AddChild(Paragraph(15, new Color(Palette.Bone, 0.5f), category.EmptyText));
            ClearEntry();
            return;
        }
        ShowEntry(first);
    }

    private void ClearEntry()
    {
        _current = null;
        _model?.QueueFree();
        _model = null;
        _castellan = null;
        _villager = null;
        _title.Text = "";
        _description.Text = "";
        _story.Text = "";
        foreach (Node child in _controls.GetChildren())
            child.QueueFree();
    }

    private void ShowEntry(Biography.Entry entry)
    {
        _current = entry;
        _title.Text = entry.Name;
        _description.Text = entry.Description;
        _story.Text = entry.Story;
        ShowModel(entry);
        BuildControls(entry);
    }

    private void BuildControls(Biography.Entry entry)
    {
        foreach (Node child in _controls.GetChildren())
            child.QueueFree();
        if (entry.Animations.Count == 0)
            return;

        var row = new HFlowContainer();
        row.AddThemeConstantOverride("h_separation", 6);
        row.AddThemeConstantOverride("v_separation", 4);
        _controls.AddChild(Caption("Animação"));
        _controls.AddChild(row);
        foreach (string animation in entry.Animations)
        {
            string a = animation;
            row.AddChild(SmallButton(a, () => PlayAnimation(a)));
        }

        if (entry.ModelKind != "villager")
            return;
        var faces = new HFlowContainer();
        faces.AddThemeConstantOverride("h_separation", 4);
        faces.AddThemeConstantOverride("v_separation", 4);
        _controls.AddChild(Caption("Expressão"));
        _controls.AddChild(faces);
        string[] faceNames = { "distraído", "esforço", "feliz", "sonolento", "dormindo", "espantado", "preocupado", "chorando", "bravo" };
        for (int i = 0; i < faceNames.Length; i++)
        {
            var face = (VillagerExpression)i;
            faces.AddChild(SmallButton(faceNames[i], () => _villagerState = _villagerState with { Expression = face }));
        }
        var hairs = new HFlowContainer();
        hairs.AddThemeConstantOverride("h_separation", 4);
        hairs.AddThemeConstantOverride("v_separation", 4);
        _controls.AddChild(Caption("Cabelo"));
        _controls.AddChild(hairs);
        for (int v = 1; v <= Villager.HairVariants; v++)
        {
            int variant = v;
            string name = VillagerLooks.HairFor(v)?.Name ?? $"{v}";
            hairs.AddChild(SmallButton(name, () =>
            {
                _villagerState = _villagerState with { HairVariant = variant };
                _villager?.ResetLook();
            }));
        }
        hairs.AddChild(SmallButton("chapéu", () => _villagerState = _villagerState with { JobResource = _villagerState.JobResource is null ? "wood" : null }));
    }

    private void PlayAnimation(string animation)
    {
        if (_castellan is not null)
            _castellan.PlayClip(animation);
        else if (_villager is not null)
            _villager.PreviewClip = animation;
        else if (_current is { ModelKind: "building" })
            _machineRunning = animation == "funcionando";
    }

    // ---- Peças de interface ----------------------------------------------------------------------------------

    private static PanelContainer Panel(CanvasLayer layer, float anchorLeft, float anchorTop, float anchorRight, float anchorBottom,
        float left, float right, float top, float bottom, float alpha = 0.72f)
    {
        var panel = new PanelContainer();
        panel.AnchorLeft = anchorLeft; panel.AnchorTop = anchorTop; panel.AnchorRight = anchorRight; panel.AnchorBottom = anchorBottom;
        panel.OffsetLeft = left; panel.OffsetRight = right; panel.OffsetTop = top; panel.OffsetBottom = bottom;
        panel.AddThemeStyleboxOverride("panel", new StyleBoxFlat
        {
            BgColor = new Color(0.06f, 0.05f, 0.09f, alpha),
            ContentMarginLeft = 22, ContentMarginRight = 22, ContentMarginTop = alpha < 0.5f ? 12 : 26, ContentMarginBottom = alpha < 0.5f ? 10 : 22,
        });
        layer.AddChild(panel);
        return panel;
    }

    private static Label Heading(string text, int size)
    {
        var label = new Label { Text = text, AutowrapMode = TextServer.AutowrapMode.Word };
        label.AddThemeFontSizeOverride("font_size", size);
        label.AddThemeColorOverride("font_color", Palette.Bone);
        return label;
    }

    private static Label Paragraph(int size, Color color, string text = "")
    {
        var label = new Label { Text = text, AutowrapMode = TextServer.AutowrapMode.Word, SizeFlagsHorizontal = Control.SizeFlags.ExpandFill };
        label.AddThemeFontSizeOverride("font_size", size);
        label.AddThemeColorOverride("font_color", color);
        return label;
    }

    private static Label Caption(string text)
    {
        var label = new Label { Text = text };
        label.AddThemeFontSizeOverride("font_size", 12);
        label.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.5f));
        return label;
    }

    private static Button MenuButton(string text, int size, Action onPressed)
    {
        var button = new Button { Text = text, Alignment = HorizontalAlignment.Left, CustomMinimumSize = new Vector2(0, 36), ClipText = true };
        button.AddThemeFontSizeOverride("font_size", size);
        button.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.85f));
        button.AddThemeColorOverride("font_hover_color", Colors.White);
        button.AddThemeColorOverride("font_disabled_color", new Color(Palette.Bone, 0.3f));
        var normal = new StyleBoxFlat { BgColor = new Color(0, 0, 0, 0), ContentMarginLeft = 10 };
        var hover = new StyleBoxFlat { BgColor = new Color(Palette.PurpleLichen, 0.35f), ContentMarginLeft = 10, CornerRadiusTopLeft = 4, CornerRadiusTopRight = 4, CornerRadiusBottomLeft = 4, CornerRadiusBottomRight = 4 };
        button.AddThemeStyleboxOverride("normal", normal);
        button.AddThemeStyleboxOverride("disabled", normal);
        button.AddThemeStyleboxOverride("hover", hover);
        button.AddThemeStyleboxOverride("pressed", hover);
        button.AddThemeStyleboxOverride("focus", new StyleBoxEmpty());
        button.Pressed += onPressed;
        return button;
    }

    private static Button SmallButton(string text, Action onPressed)
    {
        var button = new Button { Text = text };
        button.AddThemeFontSizeOverride("font_size", 13);
        button.AddThemeColorOverride("font_color", Palette.Bone);
        button.AddThemeStyleboxOverride("normal", new StyleBoxFlat { BgColor = new Color(Palette.DeepPurple, 0.9f), ContentMarginLeft = 10, ContentMarginRight = 10, ContentMarginTop = 4, ContentMarginBottom = 4, CornerRadiusTopLeft = 4, CornerRadiusTopRight = 4, CornerRadiusBottomLeft = 4, CornerRadiusBottomRight = 4 });
        button.AddThemeStyleboxOverride("hover", new StyleBoxFlat { BgColor = new Color(Palette.PurpleLichen, 0.7f), ContentMarginLeft = 10, ContentMarginRight = 10, ContentMarginTop = 4, ContentMarginBottom = 4, CornerRadiusTopLeft = 4, CornerRadiusTopRight = 4, CornerRadiusBottomLeft = 4, CornerRadiusBottomRight = 4 });
        button.AddThemeStyleboxOverride("pressed", new StyleBoxFlat { BgColor = new Color(Palette.PurpleLichen, 0.9f), ContentMarginLeft = 10, ContentMarginRight = 10, ContentMarginTop = 4, ContentMarginBottom = 4 });
        button.AddThemeStyleboxOverride("focus", new StyleBoxEmpty());
        button.Pressed += onPressed;
        return button;
    }
}
