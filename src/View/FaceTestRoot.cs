using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Cena de teste do rosto (scenes/tests/FaceTest.tscn): um aldeão (o corpo da arte quando existe; senão, ou com
/// <see cref="UsePlaceholder"/>, o placeholder de esfera com os retalhos e o atlas provisório) de perto, percorrendo as 9 expressões do GDD
/// a cada <see cref="SecondsPerExpression"/> segundos e piscando pelo <see cref="FaceAnimator"/>. Os atlas
/// aparecem embaixo, para conferir qual célula está no rosto.
/// Teclas: Espaço pausa a troca; H desce o cabelo sobre os olhos (o cabelo opaco tem de esconder o rosto onde
/// passa na frente); 5 põe <see cref="CrowdSize"/> aldeões atrás, para medir o custo do rosto (o rótulo mostra
/// os FPS); Esc volta ao menu. FaceTestCrowd.tscn abre já com H e 5 ligados.
/// </summary>
public partial class FaceTestRoot : Node3D
{
    private const float SecondsPerExpression = 1.5f;
    private const int CrowdSize = 500;

    [Export] public bool StartWithCrowd;
    [Export] public bool StartWithHairOverEyes;
    /// <summary>Força o placeholder mesmo com o corpo da arte presente.</summary>
    [Export] public bool UsePlaceholder;

    private VillagerVisual _visual = null!;
    private readonly List<VillagerVisual> _crowd = new();
    private Label _label = null!;
    private float _time;
    private int _index;
    private bool _paused, _hairOverEyes;

    public override void _Ready()
    {
        var ground = new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(16f, 16f), Material = new StandardMaterial3D { AlbedoColor = Palette.PurpleEarth, Roughness = 1f } },
        };
        AddChild(ground);

        var sun = new DirectionalLight3D { Name = "Sun", LightColor = new Color(0.72f, 0.78f, 0.9f), LightEnergy = 1.1f, ShadowEnabled = true };
        AddChild(sun);
        sun.Position = new Vector3(1f, 2f, -2f);
        sun.LookAt(new Vector3(0f, 0.3f, 0f), Vector3.Up);

        // O aldeão fica na célula (0, 0): o visual soma 0,5, então a posição de desenho é (-0,5, -0,5).
        _visual = new VillagerVisual { Name = "Villager", ForcePlaceholder = UsePlaceholder, Seed = 1 };
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

        // Os dois atlas (da arte ou provisórios), para conferir a célula escolhida.
        bool provisional = VillagerLooks.Face().Provisional;
        // Escalados para ~160 px de largura, qualquer que seja o tamanho do atlas.
        Texture2D eyesAtlas = VillagerLooks.EyesAtlas(), mouthAtlas = VillagerLooks.MouthAtlas();
        var eyes = new TextureRect { Texture = eyesAtlas, Position = new Vector2(16f, 470f), Scale = Vector2.One * (160f / eyesAtlas.GetWidth()) };
        var mouth = new TextureRect { Texture = mouthAtlas, Position = new Vector2(190f, 470f), Scale = Vector2.One * (160f / mouthAtlas.GetWidth()) };
        hud.AddChild(eyes);
        hud.AddChild(mouth);
        string tag = provisional ? "(provisório)" : "(da arte)";
        var caption = new Label { Text = $"olhos.png {tag}              boca.png {tag}", Position = new Vector2(16f, 575f) };
        caption.AddThemeFontSizeOverride("font_size", 14);
        caption.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.7f));
        hud.AddChild(caption);

        if (StartWithCrowd)
        {
            // Medição de desempenho só vale em tela cheia na Retina; lançada pelo editor a janela abre pequena.
            DisplayServer.WindowSetMode(DisplayServer.WindowMode.Fullscreen);
            ToggleCrowd();
        }
        if (StartWithHairOverEyes)
            ToggleHairOverEyes();
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is not InputEventKey { Pressed: true, Echo: false } key)
            return;
        switch (key.PhysicalKeycode)
        {
            case Key.Space: _paused = !_paused; break;
            case Key.H: ToggleHairOverEyes(); break;
            case Key.Key5: ToggleCrowd(); break;
            case Key.Escape: GetTree().ChangeSceneToFile(GameFiles.MenuScene); break;
        }
    }

    /// <summary>Desce o tufo de cabelo até cobrir os olhos: o rosto (sem escrever profundidade) tem de sumir atrás dele.</summary>
    private void ToggleHairOverEyes()
    {
        _hairOverEyes = !_hairOverEyes;
        if (_visual.HairSocket?.GetNodeOrNull<Node3D>("HairPiece") is Node3D hair)
            hair.Position += new Vector3(0f, _hairOverEyes ? -0.075f : 0.075f, _hairOverEyes ? -0.025f : 0.025f);
    }

    /// <summary>500 aldeões em fileiras atrás do principal, virados para a câmera, com o rosto trocando e piscando.</summary>
    private void ToggleCrowd()
    {
        if (_crowd.Count > 0)
        {
            foreach (VillagerVisual v in _crowd)
                v.QueueFree();
            _crowd.Clear();
            return;
        }
        for (int i = 0; i < CrowdSize; i++)
        {
            var v = new VillagerVisual { Name = $"Crowd_{i}", ForcePlaceholder = UsePlaceholder, Seed = 100 + i };
            AddChild(v);
            _crowd.Add(v);
        }
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

        // Multidão: 25 por fileira, 0,3 m entre eles, fileiras a partir de 1 m atrás, cada um numa expressão.
        for (int i = 0; i < _crowd.Count; i++)
        {
            int column = i % 25, row = i / 25;
            var pos = new System.Numerics.Vector2(-0.5f + (column - 12) * 0.3f, -0.5f + 1f + row * 0.3f);
            var e = VillagerExpressions.All[(i + _index) % VillagerExpressions.All.Length];
            _crowd[i].UpdateFrom(new VillagerVisual.DrawState(pos, new System.Numerics.Vector2(0f, -1f), 1 + i % Villager.HairVariants, e,
                e == VillagerExpression.Sleeping, null, null, -1f, 0f), null, dt);
        }

        _label.Text = $"{_index + 1}/9  {VillagerExpressions.Name(expression)}{(_visual.IsBlinking ? "   (piscando)" : "")}" +
            $"     {Engine.GetFramesPerSecond():0} FPS   aldeões {1 + _crowd.Count}{(_hairOverEyes ? "   cabelo sobre os olhos" : "")}\n" +
            "Espaço pausa  ·  H cabelo sobre os olhos  ·  5 multidão de 500  ·  Esc volta ao menu";
    }
}
