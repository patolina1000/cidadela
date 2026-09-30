using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Painel do aldeão escolhido (clique nele): nome, atributos, estado em palavras e a ladainha em blocos
/// (<see cref="LitanyBlocks"/>). Só para ver; Esc ou clicar no chão fecha.
/// </summary>
public partial class VillagerPanel : PanelContainer
{
    private Label _title = null!, _state = null!;
    private LitanyBlocks _blocks = null!;
    private SimWorld _world = null!;
    private bool _recordingShown;

    /// <summary>Por que o aldeão recusou a ladainha (a interface diz; docs/ladainhas.md).</summary>
    public static string RefusalText(LitanyFit fit) => fit switch
    {
        LitanyFit.TooLong => "RECUSOU: comandos demais para a Inteligência dele.",
        LitanyFit.TooHard => "RECUSOU: um comando que a Inteligência dele não entende.",
        LitanyFit.Empty => "RECUSOU: nada foi gravado.",
        _ => "",
    };

    /// <summary>O aldeão mostrado, ou null (painel escondido).</summary>
    public Villager? Villager { get; private set; }

    public void Build(SimWorld world)
    {
        _world = world;
        AnchorLeft = 0f; AnchorTop = 0f;
        OffsetLeft = 16f; OffsetTop = 150f;
        MouseFilter = MouseFilterEnum.Ignore;
        var style = new StyleBoxFlat { BgColor = new Color(0.08f, 0.06f, 0.11f, 0.9f), BorderColor = Palette.PurpleLichen };
        style.SetBorderWidthAll(2);
        style.SetCornerRadiusAll(6);
        style.SetContentMarginAll(12f);
        AddThemeStyleboxOverride("panel", style);
        var box = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        box.AddThemeConstantOverride("separation", 8);
        AddChild(box);
        _title = new Label();
        _title.AddThemeFontSizeOverride("font_size", 18);
        _title.AddThemeColorOverride("font_color", Palette.Bone);
        box.AddChild(_title);
        _state = new Label { AutowrapMode = TextServer.AutowrapMode.WordSmart, CustomMinimumSize = new Vector2(420f, 0f) };
        _state.AddThemeFontSizeOverride("font_size", 14);
        box.AddChild(_state);
        _blocks = new LitanyBlocks { MouseFilter = MouseFilterEnum.Ignore };
        box.AddChild(_blocks);
        Visible = false;
    }

    public void ShowVillager(Villager? villager)
    {
        Villager = villager;
        Visible = villager is not null;
        _blocks.Show(_world, villager);
    }

    public override void _Process(double delta)
    {
        if (Villager is not Villager v)
            return;
        if (_world.Teaching is TeachingSession session && session.Villager == v)
        {
            // Gravando: os blocos são o que ela já fez.
            _title.Text = $"ENSINANDO o aldeão {v.Id}   ·   {session.Commands.Count}/{v.Stats.MaxCommands(v.Intelligence)} comandos";
            _state.Text = (_world.LastTeachResult is LitanyFit fit && fit != LitanyFit.Ok ? RefusalText(fit) + "\n" : "") +
                "Faça a tarefa: colher, pegar (clique no baú ou máquina), pôr (item na mão), operar (E).\n" +
                "G marca \"ir até\" aqui   ·   Enter: pronto   ·   Esc: cancelar";
            _state.AddThemeColorOverride("font_color", Palette.Sickly);
            _blocks.ShowRecording(_world, session.Commands);
            _recordingShown = true;
            return;
        }
        if (_recordingShown)
        {
            _recordingShown = false;
            _blocks.Show(_world, v);
        }
        _title.Text = $"Aldeão {v.Id}   ·   Força {v.Strength}  Agilidade {v.Agility}  Inteligência {v.Intelligence}";
        string carrying = v.CarryingCount > 0 ? $"   ·   leva {v.CarryingCount} {_world.Data.Item(v.CarryingKind!).Name.ToLowerInvariant()}" : "";
        _state.Text = v.Litany is null
            ? "Sem ladainha: parado. (O aldeão não faz nada sozinho.)   T: ensinar" + carrying
            : v.Stuck is LitanyStuck reason
                ? $"TRAVADO em \"{LitanyText.Command(v.CurrentCommand!, _world)}\": {LitanyText.Stuck(reason, v.CurrentCommand, _world)}" + carrying
                : $"Ladainha \"{v.Litany.Name}\" ({v.Litany.Commands.Count}/{v.Stats.MaxCommands(v.Intelligence)} comandos)" + carrying;
        _state.AddThemeColorOverride("font_color", v.Stuck is not null ? Palette.Pumpkin : new Color(0.85f, 0.85f, 0.9f));
        if (_blocks.CustomMinimumSize.Y < 1f && v.Litany is not null)
            _blocks.Show(_world, v);
    }
}
