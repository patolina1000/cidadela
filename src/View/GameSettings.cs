using Godot;

namespace Cidadela.View;

/// <summary>
/// Configurações do jogador (tela cheia e V-Sync), salvas em user://settings.cfg e aplicadas ao abrir o jogo.
/// Sem arquivo, vale o que o project.godot define. Não são dados de design, por isso não ficam em data/.
/// </summary>
public static class GameSettings
{
    private const string Path = "user://settings.cfg";
    private const string Section = "video";

    private static bool _applied;

    public static bool Fullscreen => DisplayServer.WindowGetMode() is DisplayServer.WindowMode.Fullscreen or DisplayServer.WindowMode.ExclusiveFullscreen;
    public static bool Vsync => DisplayServer.WindowGetVsyncMode() != DisplayServer.VSyncMode.Disabled;

    /// <summary>Aplica o arquivo salvo uma vez por execução. Chamado pela primeira cena que abrir (menu ou jogo).</summary>
    public static void EnsureApplied()
    {
        if (_applied)
            return;
        _applied = true;
        var file = new ConfigFile();
        if (file.Load(Path) != Error.Ok)
            return;
        ApplyFullscreen((bool)file.GetValue(Section, "fullscreen", Fullscreen));
        ApplyVsync((bool)file.GetValue(Section, "vsync", Vsync));
        GD.Print($"[config] {Path}: tela cheia {Fullscreen}, V-Sync {Vsync}");
    }

    public static void SetFullscreen(bool on)
    {
        ApplyFullscreen(on);
        Save();
    }

    public static void SetVsync(bool on)
    {
        ApplyVsync(on);
        Save();
    }

    private static void ApplyFullscreen(bool on)
    {
        if (on != Fullscreen)
            DisplayServer.WindowSetMode(on ? DisplayServer.WindowMode.Fullscreen : DisplayServer.WindowMode.Windowed);
    }

    private static void ApplyVsync(bool on) =>
        DisplayServer.WindowSetVsyncMode(on ? DisplayServer.VSyncMode.Enabled : DisplayServer.VSyncMode.Disabled);

    private static void Save()
    {
        var file = new ConfigFile();
        file.SetValue(Section, "fullscreen", Fullscreen);
        file.SetValue(Section, "vsync", Vsync);
        Error error = file.Save(Path);
        if (error != Error.Ok)
            GD.PushWarning($"[config] não salvou {Path}: {error}");
    }
}
