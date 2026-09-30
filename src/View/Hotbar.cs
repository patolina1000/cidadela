using System;
using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Barra de construção no pé da tela: um botão por construção, na ordem de data/buildings.json, em páginas de
/// <see cref="PageSize"/> (teclas 1 a 9 dentro da página; Tab troca de página). Clicar no escolhido de novo desmarca.
/// </summary>
public partial class Hotbar : HBoxContainer
{
    public const int PageSize = 9;

    /// <summary>A página à vista (0 = a primeira).</summary>
    public int Page { get; private set; }

    /// <summary>Quantas páginas há.</summary>
    public int PageCount => Math.Max(1, (_buttons.Count + PageSize - 1) / PageSize);

    /// <summary>Índice escolhido pelo clique, ou null se desmarcou.</summary>
    public event Action<int?>? SlotClicked;

    /// <summary>Estilo do botão escolhido (borda verde), compartilhado com a <see cref="InventoryBar"/>.</summary>
    public static readonly StyleBoxFlat SelectedStyle = new()
    {
        BgColor = new Color(0.12f, 0.16f, 0.08f, 0.92f),
        BorderColor = Palette.Sickly,
        BorderWidthLeft = 3,
        BorderWidthTop = 3,
        BorderWidthRight = 3,
        BorderWidthBottom = 3,
        CornerRadiusTopLeft = 4,
        CornerRadiusTopRight = 4,
        CornerRadiusBottomLeft = 4,
        CornerRadiusBottomRight = 4,
    };

    private readonly List<Button> _buttons = new();
    private IReadOnlyList<BuildingType> _types = Array.Empty<BuildingType>();

    public void Build(IReadOnlyList<BuildingType> types, GameData data)
    {
        _types = types;
        Alignment = AlignmentMode.Center;
        AddThemeConstantOverride("separation", 8);
        AnchorLeft = 0f;
        AnchorRight = 1f;
        AnchorTop = 1f;
        AnchorBottom = 1f;
        OffsetTop = -78f;
        OffsetBottom = -12f;

        for (int i = 0; i < types.Count; i++)
        {
            BuildingType type = types[i];
            var costs = new List<string>();
            foreach ((string item, int amount) in type.Cost)
                costs.Add($"{amount} {data.Item(item).Name}");

            int index = i;
            var button = new Button
            {
                Text = $"{i % PageSize + 1}  {type.Name}\n{string.Join(", ", costs)}",
                ToggleMode = true,
                FocusMode = FocusModeEnum.None,
                CustomMinimumSize = new Vector2(104f, 62f),
            };
            button.AddThemeFontSizeOverride("font_size", 11);
            // O tema padrão quase não diferencia o botão escolhido: borda e texto verdes deixam claro.
            button.AddThemeStyleboxOverride("pressed", SelectedStyle);
            button.AddThemeStyleboxOverride("hover_pressed", SelectedStyle);
            button.AddThemeColorOverride("font_pressed_color", Palette.Sickly);
            button.AddThemeColorOverride("font_hover_pressed_color", Palette.Sickly);
            button.Pressed += () => SlotClicked?.Invoke(button.ButtonPressed ? index : null);
            AddChild(button);
            _buttons.Add(button);
        }
    }

    /// <summary>Mostra só os botões de uma página (Tab); com mais de uma, o último botão da página diz "Tab".</summary>
    public void ShowPage(int page)
    {
        Page = ((page % PageCount) + PageCount) % PageCount;
        for (int i = 0; i < _buttons.Count; i++)
            _buttons[i].Visible = i / PageSize == Page;
        TooltipText = PageCount > 1 ? $"Página {Page + 1}/{PageCount} (Tab troca)" : "";
    }

    /// <summary>Marca o botão escolhido (ou nenhum) sem disparar <see cref="SlotClicked"/>.</summary>
    public void ShowSelected(int? index)
    {
        for (int i = 0; i < _buttons.Count; i++)
            _buttons[i].SetPressedNoSignal(i == index);
    }

    /// <summary>Apaga os botões das construções que o inventário não paga.</summary>
    public void ShowAffordable(Inventory inventory)
    {
        for (int i = 0; i < _buttons.Count; i++)
            _buttons[i].Modulate = inventory.Has(_types[i].Cost) ? Colors.White : new Color(1f, 1f, 1f, 0.45f);
    }
}
