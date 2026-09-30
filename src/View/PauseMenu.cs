using Godot;

namespace Cidadela.View;

/// <summary>
/// Menu de pausa do jogo (Esc): Continuar, Configurações, Menu inicial e Sair, no visual do menu inicial.
/// Aberto, pausa a árvore inteira (simulação, câmera e animações); só este menu continua processando.
/// Esc fecha as Configurações e, depois, o menu.
/// </summary>
public partial class PauseMenu : CanvasLayer
{
    private SettingsPanel _settings = null!;

    public bool IsOpen => Visible;

    public override void _Ready()
    {
        Layer = 10; // acima do HUD do jogo
        ProcessMode = ProcessModeEnum.Always;
        Visible = false;

        var dim = new ColorRect { Name = "Dim", Color = new Color(0.03f, 0.02f, 0.05f, 0.45f) };
        dim.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(dim);

        VBoxContainer column = MenuStyle.AddLeftPanel(this);
        MenuStyle.AddTitle(column, "pausado");
        MenuStyle.AddButton(column, "Continuar", Close);
        MenuStyle.AddButton(column, "Configurações", () => _settings.Visible = !_settings.Visible);
        MenuStyle.AddButton(column, "Menu inicial", () =>
        {
            GetTree().Paused = false;
            GetTree().ChangeSceneToFile(GameFiles.MenuScene);
        });
        MenuStyle.AddButton(column, "Sair", () => GetTree().Quit());

        _settings = new SettingsPanel();
        AddChild(_settings);
    }

    public void Open()
    {
        Visible = true;
        GetTree().Paused = true;
    }

    public void Close()
    {
        _settings.Visible = false;
        Visible = false;
        GetTree().Paused = false;
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (!Visible || @event is not InputEventKey { Pressed: true, Echo: false, PhysicalKeycode: Key.Escape })
            return;
        if (_settings.Visible)
            _settings.Visible = false;
        else
            Close();
        GetViewport().SetInputAsHandled();
    }
}
