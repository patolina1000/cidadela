using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Rosto de um aldeão na view: aplica o shader do rosto nas malhas "Olhos" e "Boca" (material compartilhado,
/// sem duplicar) e, a cada quadro, pede ao <see cref="FaceAnimator"/> (C# puro: expressão → quadros, piscar)
/// qual célula mostrar, gravando só o índice como parâmetro de instância ("frame").
/// </summary>
public sealed class VillagerFace
{
    private static readonly HashSet<string> _warned = new();

    private readonly MeshInstance3D? _eyes, _mouth;
    private readonly FaceAnimator _animator;
    private readonly VillagerLooks.FaceInfo _info;
    private int _eyesFrame = -1, _mouthFrame = -1;

    /// <summary>Se os olhos estão fechados por um piscar (para a cena de teste mostrar).</summary>
    public bool Blinking => _animator.Blinking;

    public VillagerFace(int seed, MeshInstance3D? eyes, MeshInstance3D? mouth)
    {
        _info = VillagerLooks.Face();
        _animator = new FaceAnimator(seed, _info.Table);
        _eyes = eyes;
        _mouth = mouth;
        if (_eyes is not null)
        {
            _eyes.MaterialOverride = VillagerLooks.EyesMaterial();
            _eyes.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        }
        if (_mouth is not null)
        {
            _mouth.MaterialOverride = VillagerLooks.MouthMaterial();
            _mouth.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        }
    }

    public void Update(float dt, VillagerExpression expression)
    {
        _animator.Advance(dt, expression);
        Apply(_eyes, ref _eyesFrame, _info.Eyes, _animator.Eyes, "olhos");
        Apply(_mouth, ref _mouthFrame, _info.Mouth, _animator.Mouth, "boca");
    }

    private static void Apply(MeshInstance3D? mesh, ref int current, VillagerLooks.FaceGrid grid, string frameName, string what)
    {
        int frame = grid.Frame(frameName);
        if (frame < 0)
        {
            if (_warned.Add(what + ":" + frameName))
                GD.PushWarning($"Aldeão: quadro de {what} \"{frameName}\" não existe no atlas; usando o quadro 0.");
            frame = 0;
        }
        if (frame == current)
            return;
        current = frame;
        mesh?.SetInstanceShaderParameter("frame", frame);
    }
}
