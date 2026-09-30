using Godot;

namespace Cidadela.View;

/// <summary>
/// Visual comum aos menus (inicial e de pausa): painel escuro no terço esquerdo, título em osso e botões sem fundo
/// que acendem em líquen roxo ao passar o mouse.
/// </summary>
public static class MenuStyle
{
    public const float PanelWidth = 400f;

    /// <summary>Painel da altura toda, colado à esquerda, com uma coluna dentro; devolve a coluna.</summary>
    public static VBoxContainer AddLeftPanel(Node parent)
    {
        var panel = new PanelContainer { Name = "Panel" };
        panel.AnchorTop = 0f; panel.AnchorBottom = 1f; panel.AnchorLeft = 0f; panel.AnchorRight = 0f;
        panel.OffsetLeft = 0f; panel.OffsetRight = PanelWidth;
        panel.AddThemeStyleboxOverride("panel", new StyleBoxFlat
        {
            BgColor = new Color(0.06f, 0.05f, 0.09f, 0.72f),
            ContentMarginLeft = 44, ContentMarginRight = 44, ContentMarginTop = 60, ContentMarginBottom = 40,
        });
        parent.AddChild(panel);

        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 10);
        panel.AddChild(column);
        return column;
    }

    /// <summary>Título do jogo, uma linha menor embaixo e um respiro antes dos botões.</summary>
    public static void AddTitle(Control column, string subtitle)
    {
        var title = new Label { Text = "Engrenagens da\nCidadela" };
        title.AddThemeFontSizeOverride("font_size", 40);
        title.AddThemeColorOverride("font_color", Palette.Bone);
        column.AddChild(title);
        var sub = new Label { Text = subtitle };
        sub.AddThemeFontSizeOverride("font_size", 15);
        sub.AddThemeColorOverride("font_color", new Color(Palette.Bone, 0.55f));
        column.AddChild(sub);
        column.AddChild(new Control { CustomMinimumSize = new Vector2(0, 30) });
    }

    private const int CheckSize = 20;
    private static Texture2D? _checked, _unchecked;

    /// <summary>
    /// Caixa de seleção com ícone próprio: a do tema padrão, desmarcada, some no fundo escuro dos painéis.
    /// Desmarcada é uma moldura em osso; marcada, a moldura com um quadrado de líquen roxo e osso dentro.
    /// </summary>
    public static CheckBox CheckBox(string text, bool pressed)
    {
        _unchecked ??= CheckIcon(false);
        _checked ??= CheckIcon(true);
        var box = new CheckBox { Text = text, ButtonPressed = pressed };
        box.AddThemeIconOverride("unchecked", _unchecked);
        box.AddThemeIconOverride("checked", _checked);
        box.AddThemeIconOverride("unchecked_disabled", _unchecked);
        box.AddThemeIconOverride("checked_disabled", _checked);
        box.AddThemeConstantOverride("h_separation", 10);
        box.AddThemeColorOverride("font_color", Palette.Bone);
        box.AddThemeColorOverride("font_hover_color", Colors.White);
        box.AddThemeColorOverride("font_pressed_color", Palette.Bone);
        box.AddThemeColorOverride("font_hover_pressed_color", Colors.White);
        box.AddThemeStyleboxOverride("focus", new StyleBoxEmpty());
        return box;
    }

    private static Texture2D CheckIcon(bool on)
    {
        var image = Image.CreateEmpty(CheckSize, CheckSize, false, Image.Format.Rgba8);
        image.Fill(new Color(0, 0, 0, 0));
        image.FillRect(new Rect2I(1, 1, CheckSize - 2, CheckSize - 2), new Color(Palette.Bone, 0.85f));
        image.FillRect(new Rect2I(3, 3, CheckSize - 6, CheckSize - 6), new Color(Palette.DeepPurple, 0.9f));
        if (on)
        {
            image.FillRect(new Rect2I(5, 5, CheckSize - 10, CheckSize - 10), Palette.PurpleLichen);
            image.FillRect(new Rect2I(7, 7, CheckSize - 14, CheckSize - 14), Palette.Bone);
        }
        return ImageTexture.CreateFromImage(image);
    }

    public static Button AddButton(Control parent, string text, System.Action onPressed)
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
}
