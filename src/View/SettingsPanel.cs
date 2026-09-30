using Godot;

namespace Cidadela.View;

/// <summary>
/// Painel de Configurações (GDD, seção 12: tela cheia e V-Sync), à direita do painel do menu.
/// Usado pelo menu inicial e pelo de pausa; cada mudança é salva na hora (<see cref="GameSettings"/>).
/// O volume fica desativado até existir som.
/// </summary>
public partial class SettingsPanel : PanelContainer
{
    public override void _Ready()
    {
        Name = "Settings";
        Visible = false;
        AnchorLeft = 0f; AnchorRight = 0f; AnchorTop = 0.5f; AnchorBottom = 0.5f;
        OffsetLeft = MenuStyle.PanelWidth + 20f; OffsetRight = MenuStyle.PanelWidth + 400f; OffsetTop = -120f; OffsetBottom = 120f;
        AddThemeStyleboxOverride("panel", new StyleBoxFlat
        {
            BgColor = new Color(0.06f, 0.05f, 0.09f, 0.85f), BorderColor = new Color(Palette.PurpleLichen, 0.6f),
            BorderWidthLeft = 1, BorderWidthTop = 1, BorderWidthRight = 1, BorderWidthBottom = 1,
            ContentMarginLeft = 24, ContentMarginRight = 24, ContentMarginTop = 18, ContentMarginBottom = 18,
        });
        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 10);
        AddChild(column);

        var title = new Label { Text = "Configurações" };
        title.AddThemeFontSizeOverride("font_size", 20);
        title.AddThemeColorOverride("font_color", Palette.Bone);
        column.AddChild(title);

        var fullscreen = new CheckBox { Text = "Tela cheia", ButtonPressed = GameSettings.Fullscreen };
        fullscreen.Toggled += GameSettings.SetFullscreen;
        column.AddChild(fullscreen);

        var vsync = new CheckBox { Text = "V-Sync", ButtonPressed = GameSettings.Vsync };
        vsync.Toggled += GameSettings.SetVsync;
        column.AddChild(vsync);

        column.AddChild(new Label { Text = "Volume (ainda sem som)" });
        column.AddChild(new HSlider { MinValue = 0, MaxValue = 100, Value = 80, Editable = false });

        // Ao abrir, mostra o estado real (a tela cheia também muda pelo sistema, e o V-Sync pela tecla do painel F3).
        VisibilityChanged += () =>
        {
            fullscreen.SetPressedNoSignal(GameSettings.Fullscreen);
            vsync.SetPressedNoSignal(GameSettings.Vsync);
        };

        var close = new Button { Text = "Fechar" };
        close.Pressed += () => Visible = false;
        column.AddChild(close);
    }
}
