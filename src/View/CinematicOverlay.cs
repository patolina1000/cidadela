using Godot;

namespace Cidadela.View;

/// <summary>Faixas pretas de cinema (em cima e embaixo) com uma legenda. Não bloqueia o mouse.</summary>
public partial class CinematicOverlay : Control
{
    private const float BarFraction = 0.1f;

    private ColorRect _top = null!;
    private ColorRect _bottom = null!;
    private Label _caption = null!;
    private float _shown;
    private float _target;

    public override void _Ready()
    {
        SetAnchorsPreset(LayoutPreset.FullRect);
        MouseFilter = MouseFilterEnum.Ignore;

        _top = new ColorRect { Color = Colors.Black, MouseFilter = MouseFilterEnum.Ignore };
        _bottom = new ColorRect { Color = Colors.Black, MouseFilter = MouseFilterEnum.Ignore };
        AddChild(_top);
        AddChild(_bottom);

        _caption = new Label
        {
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        _caption.AddThemeFontSizeOverride("font_size", 16);
        _caption.AddThemeColorOverride("font_color", Palette.Bone);
        AddChild(_caption);
        Visible = false;
    }

    public void Show(bool on) => _target = on ? 1f : 0f;

    public void SetCaption(string text) => _caption.Text = text;

    public override void _Process(double delta)
    {
        _shown = Mathf.MoveToward(_shown, _target, (float)delta * 3f);
        Visible = _shown > 0f;
        if (!Visible)
            return;

        // Faixas entram com curva suave; a legenda aparece junto.
        float eased = _shown * _shown * (3f - 2f * _shown);
        Vector2 size = GetViewportRect().Size;
        float bar = size.Y * BarFraction * eased;
        _top.Position = Vector2.Zero;
        _top.Size = new Vector2(size.X, bar);
        _bottom.Position = new Vector2(0f, size.Y - bar);
        _bottom.Size = new Vector2(size.X, bar);
        _caption.Position = _bottom.Position;
        _caption.Size = new Vector2(size.X, bar);
        _caption.Modulate = new Color(1f, 1f, 1f, eased);
    }
}
