using System;
using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Inventário do Castelão como botões ("Madeira: 12"). Clicar segura aquele item na mão
/// para pôr em esteiras e baús; clicar de novo solta.
/// </summary>
public partial class InventoryBar : HBoxContainer
{
    /// <summary>Tipo escolhido pelo clique, ou null se soltou.</summary>
    public event Action<string?>? ItemClicked;

    private readonly List<(ResourceType Type, Button Button)> _slots = new();

    public void Build(IEnumerable<ResourceType> types)
    {
        AddThemeConstantOverride("separation", 6);
        Position = new Vector2(12f, 36f);

        foreach (ResourceType type in types)
        {
            var button = new Button
            {
                ToggleMode = true,
                FocusMode = FocusModeEnum.None,
                CustomMinimumSize = new Vector2(104f, 30f),
            };
            button.AddThemeFontSizeOverride("font_size", 13);
            button.AddThemeStyleboxOverride("pressed", Hotbar.SelectedStyle);
            button.AddThemeStyleboxOverride("hover_pressed", Hotbar.SelectedStyle);
            button.AddThemeColorOverride("font_pressed_color", Palette.Sickly);
            button.AddThemeColorOverride("font_hover_pressed_color", Palette.Sickly);
            string kind = type.Kind;
            button.Pressed += () => ItemClicked?.Invoke(button.ButtonPressed ? kind : null);
            AddChild(button);
            _slots.Add((type, button));
        }
    }

    public void ShowHeld(string? kind)
    {
        foreach ((ResourceType type, Button button) in _slots)
            button.SetPressedNoSignal(type.Kind == kind);
    }

    public void ShowCounts(Inventory inventory)
    {
        foreach ((ResourceType type, Button button) in _slots)
        {
            int count = inventory.Count(type.Kind);
            button.Text = $"{type.Name}: {count}";
            button.Modulate = count > 0 ? Colors.White : new Color(1f, 1f, 1f, 0.5f);
        }
    }
}
