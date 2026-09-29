using System.Text;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Painel de desempenho (F3): FPS, tempo de quadro, tempo de CPU, chamadas de desenho, primitivos, objetos,
/// memória de vídeo e resolução 3D. As teclas F4–F10 ligam e desligam partes da cena para isolar o custo de
/// cada uma (grama, brilho, névoa, sombra do sol, chão, escala 3D, pós-processo). No Metal o Godot não mede
/// tempo de GPU, e o monitor TIME_PROCESS inclui a espera pela GPU; por isso o tempo de CPU do jogo é medido
/// aqui mesmo (<see cref="GameCpuMs"/>, cronometrado pelo GameRoot em volta da simulação e da view). Se o
/// quadro dura bem mais que isso, o resto é renderização (GPU ou servidor de render).
/// </summary>
public partial class PerfOverlay : Label
{
    private static readonly float[] Scales = { 1f, 0.77f, 0.67f, 0.5f };

    private WorldView _view = null!;
    private Environment _environment = null!;
    private DirectionalLight3D _sun = null!;
    private CanvasItem _vignette = null!;
    private float _sunAngularDistance;
    private int _scaleIndex;
    private double _accum;
    private double _cpuMax;

    /// <summary>Tempo de CPU do último quadro gasto em simulação + view (medido pelo GameRoot), em ms.</summary>
    public double GameCpuMs { get; set; }

    public void Setup(WorldView view, WorldEnvironment environment, DirectionalLight3D sun, CanvasItem vignette)
    {
        _view = view;
        _environment = environment.Environment;
        _sun = sun;
        _sunAngularDistance = sun.LightAngularDistance;
        _vignette = vignette;
        Visible = false;
        Position = new Vector2(12f, 104f);
        AddThemeColorOverride("font_color", new Color(0.93f, 0.9f, 0.84f));
        AddThemeColorOverride("font_outline_color", Colors.Black);
        AddThemeConstantOverride("outline_size", 4);
    }

    /// <summary>Trata as teclas do painel; devolve true se consumiu a tecla.</summary>
    public bool HandleKey(Key key)
    {
        switch (key)
        {
            case Key.F3: Visible = !Visible; return true;
            case Key.F1:
                // Penumbra que cresce com a distância (PCSS): cara na filtragem por pixel. O desfoque fixo continua.
                _sun.LightAngularDistance = _sun.LightAngularDistance > 0f ? 0f : _sunAngularDistance;
                return true;
            case Key.F2:
                // Sem V-Sync o quadro mostra o tempo real de renderização (com ele, trava em múltiplos de 1/120 s).
                DisplayServer.WindowSetVsyncMode(VsyncOn ? DisplayServer.VSyncMode.Disabled : DisplayServer.VSyncMode.Enabled);
                return true;
            case Key.F4: _view.Grass.Visible = !_view.Grass.Visible; return true;
            case Key.F5: _environment.GlowEnabled = !_environment.GlowEnabled; return true;
            case Key.F6: _environment.FogEnabled = !_environment.FogEnabled; return true;
            case Key.F7: _sun.ShadowEnabled = !_sun.ShadowEnabled; return true;
            case Key.F8: _view.Ground.Visible = !_view.Ground.Visible; return true;
            case Key.F9:
                _scaleIndex = (_scaleIndex + 1) % Scales.Length;
                GetViewport().Scaling3DMode = Scales[_scaleIndex] < 1f ? Viewport.Scaling3DModeEnum.Fsr2 : Viewport.Scaling3DModeEnum.Bilinear;
                GetViewport().Scaling3DScale = Scales[_scaleIndex];
                return true;
            case Key.F10:
                _environment.AdjustmentEnabled = !_environment.AdjustmentEnabled;
                _vignette.Visible = _environment.AdjustmentEnabled;
                return true;
            case Key.F11:
                SaveScreenshot();
                return true;
            case Key.F12:
                _view.Grass.LodEnabled = !_view.Grass.LodEnabled;
                return true;
            default:
                return false;
        }
    }

    public override void _Process(double delta)
    {
        if (!Visible)
            return;
        _accum += delta;
        if (_accum < 0.25)
            return;
        _accum = 0;

        double fps = Engine.GetFramesPerSecond();
        double frameMs = fps > 0 ? 1000.0 / fps : 0;
        double cpuMs = GameCpuMs;
        _cpuMax = System.Math.Max(_cpuMax * 0.9, cpuMs);
        Vector2I size = DisplayServer.WindowGetSize();
        float scale = GetViewport().Scaling3DScale;

        var sb = new StringBuilder();
        // Em segundo plano o macOS reduz o jogo: as medições não valem.
        if (!GetWindow().HasFocus())
            sb.AppendLine("[JANELA SEM FOCO: medição inválida]");
        sb.AppendLine($"{fps:0} FPS  quadro {frameMs:0.0} ms  |  CPU do jogo {cpuMs:0.0} ms (pico {_cpuMax:0.0})  |  " +
            (frameMs > cpuMs * 2 ? "gargalo: renderização" : "gargalo: CPU do jogo"));
        sb.AppendLine($"draw calls {Performance.GetMonitor(Performance.Monitor.RenderTotalDrawCallsInFrame):0}  |  " +
            $"primitivos {Performance.GetMonitor(Performance.Monitor.RenderTotalPrimitivesInFrame) / 1e6:0.00} M  |  " +
            $"objetos {Performance.GetMonitor(Performance.Monitor.RenderTotalObjectsInFrame):0}  |  " +
            $"nós {Performance.GetMonitor(Performance.Monitor.ObjectNodeCount):0}  |  " +
            $"VRAM {Performance.GetMonitor(Performance.Monitor.RenderVideoMemUsed) / 1048576.0:0} MB");
        sb.AppendLine($"tela {size.X}x{size.Y}  3D {(int)(size.X * scale)}x{(int)(size.Y * scale)} (escala {scale:0.00})  |  grama {_view.GrassTufts} tufos");
        sb.Append($"F1 penumbra {OnOff(_sun.LightAngularDistance > 0f)}  F2 V-Sync {OnOff(VsyncOn)}  F4 grama {OnOff(_view.Grass.Visible)}  F5 brilho {OnOff(_environment.GlowEnabled)}  F6 névoa {OnOff(_environment.FogEnabled)}  " +
            $"F7 sombra {OnOff(_sun.ShadowEnabled)}  F8 chão {OnOff(_view.Ground.Visible)}  F9 escala 3D  F10 pós {OnOff(_environment.AdjustmentEnabled)}  " +
            $"F11 captura  F12 LOD grama {OnOff(_view.Grass.LodEnabled)}");
        Text = sb.ToString();
    }

    /// <summary>Captura em resolução total em docs/prints/captura_N.png (o MCP só transporta 640 px).</summary>
    private void SaveScreenshot()
    {
        string dir = ProjectSettings.GlobalizePath("res://docs/prints/");
        int n = 1;
        while (System.IO.File.Exists(System.IO.Path.Combine(dir, $"captura_{n}.png")))
            n++;
        string path = System.IO.Path.Combine(dir, $"captura_{n}.png");
        GetViewport().GetTexture().GetImage().SavePng(path);
        GD.Print($"[perf] captura salva em {path}");
    }

    private static bool VsyncOn => DisplayServer.WindowGetVsyncMode() != DisplayServer.VSyncMode.Disabled;

    private static string OnOff(bool on) => on ? "[on]" : "[off]";
}
