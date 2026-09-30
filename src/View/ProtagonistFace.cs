using System.Collections.Generic;
using System.Text.Json;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Rosto da protagonista v2 (assets/modelos/protagonista_v2/rosto/rosto.json, formato do aldeão): o shader do rosto nos
/// retalhos "Olhos" e "Boca" com o atlas dela, a expressão pelo nome ("neutra_cansada", "esforco", ...) e o piscar em três
/// quadros, meio fechado → fechado → meio fechado, com os mesmos tempos do aldeão (<see cref="Simulation.FaceAnimator"/>).
/// </summary>
public sealed class ProtagonistFace
{
    public const string Neutral = "neutra_cansada";
    public const string Effort = "esforco";

    private const string FacePath = "res://assets/modelos/protagonista_v2/rosto/rosto.json";
    private const string HalfClosed = "meio_fechado", Closed = "fechado";

    private readonly MeshInstance3D? _eyes, _mouth;
    private readonly Dictionary<string, int> _eyeFrames = new(), _mouthFrames = new();
    private readonly Dictionary<string, (string Eyes, string Mouth)> _expressions = new();
    private readonly RandomNumberGenerator _rng = new();
    private float _untilBlink, _blink = -1f;
    private int _eyesFrame = -1, _mouthFrame = -1;

    public ProtagonistFace(MeshInstance3D? eyes, MeshInstance3D? mouth, float shadowFloor)
    {
        _eyes = eyes;
        _mouth = mouth;
        _rng.Seed = 7;
        _untilBlink = NextInterval();
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(FacePath), VillagerLooks.JsonOptions);
        JsonElement root = doc.RootElement;
        Setup(eyes, root.GetProperty("olhos"), "olhos.png", _eyeFrames, shadowFloor);
        Setup(mouth, root.GetProperty("boca"), "boca.png", _mouthFrames, shadowFloor);
        foreach (JsonProperty e in root.GetProperty("expressoes").EnumerateObject())
            _expressions[e.Name] = (e.Value.GetProperty("olhos").GetString() ?? "", e.Value.GetProperty("boca").GetString() ?? "");
    }

    public void Update(float dt, string expression)
    {
        if (!_expressions.TryGetValue(expression, out (string Eyes, string Mouth) frames) &&
            !_expressions.TryGetValue(Neutral, out frames))
            return;
        if (_blink >= 0f)
        {
            _blink += dt;
            if (_blink >= Simulation.FaceAnimator.BlinkSeconds)
                _blink = -1f;
        }
        else if ((_untilBlink -= dt) <= 0f)
        {
            _blink = 0f;
            _untilBlink = NextInterval();
        }
        string eyes = _blink < 0f ? frames.Eyes
            : _blink < Simulation.FaceAnimator.HalfClosedSeconds ? HalfClosed
            : _blink < Simulation.FaceAnimator.HalfClosedSeconds + Simulation.FaceAnimator.ClosedSeconds ? Closed
            : HalfClosed;
        Apply(_eyes, _eyeFrames, eyes, ref _eyesFrame);
        Apply(_mouth, _mouthFrames, frames.Mouth, ref _mouthFrame);
    }

    private static void Setup(MeshInstance3D? mesh, JsonElement grid, string atlas, Dictionary<string, int> frames, float shadowFloor)
    {
        foreach (JsonProperty f in grid.GetProperty("quadros").EnumerateObject())
            frames[f.Name] = f.Value.GetInt32();
        if (mesh is null)
            return;
        var material = new ShaderMaterial { Shader = GD.Load<Shader>(VillagerLooks.FaceShaderPath) };
        material.SetShaderParameter("atlas", GD.Load<Texture2D>(FacePath[..(FacePath.LastIndexOf('/') + 1)] + atlas));
        material.SetShaderParameter("columns", grid.GetProperty("colunas").GetInt32());
        material.SetShaderParameter("rows", grid.GetProperty("linhas").GetInt32());
        material.SetShaderParameter("shadow_floor", shadowFloor);
        mesh.MaterialOverride = material;
        mesh.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
    }

    private static void Apply(MeshInstance3D? mesh, Dictionary<string, int> frames, string name, ref int current)
    {
        if (!frames.TryGetValue(name, out int frame) || frame == current)
            return;
        current = frame;
        mesh?.SetInstanceShaderParameter("frame", frame);
    }

    private float NextInterval() =>
        _rng.RandfRange(Simulation.FaceAnimator.MinBlinkInterval, Simulation.FaceAnimator.MaxBlinkInterval);
}
