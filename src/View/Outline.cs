using System;
using System.Collections.Generic;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Contorno fino escuro (Outline.gdshader) como segundo passe dos materiais registrados: árvores, pedras, veios,
/// aldeões, protagonista e construções. Um material de contorno compartilhado (e uma variante com o recorte em volta
/// da protagonista, para as árvores). <see cref="Enabled"/> liga e desliga tudo (tecla O no jogo), tirando e repondo o
/// passe. Cor, espessura em pixels e o estado inicial vêm de data/visual.json ("outline").
/// </summary>
public static class Outline
{
    private static readonly List<(WeakReference<Material> Material, bool Occluding)> Attached = new();
    private static ShaderMaterial? _pass, _occludingPass;
    private static bool? _enabled;

    public static bool Enabled
    {
        get => _enabled ??= VisualSettings.Current.Outline.Enabled;
        set
        {
            _enabled = value;
            Attached.RemoveAll(entry => !entry.Material.TryGetTarget(out _));
            foreach ((WeakReference<Material> reference, bool occluding) in Attached)
                if (reference.TryGetTarget(out Material? material))
                    material.NextPass = value ? PassFor(occluding) : null;
        }
    }

    /// <summary>Põe o contorno como segundo passe do material (e o registra para a tecla O).</summary>
    public static void Attach(Material material, bool occluding = false)
    {
        Attached.Add((new WeakReference<Material>(material), occluding));
        material.NextPass = Enabled ? PassFor(occluding) : null;
    }

    /// <summary>Centro do recorte (o peito da protagonista) na variante das árvores; null desliga.</summary>
    public static void SetOcclusionCenter(Vector3? center)
    {
        ShaderMaterial pass = PassFor(occluding: true);
        pass.SetShaderParameter("occlusion_enabled", center is not null);
        if (center is Vector3 c)
            pass.SetShaderParameter("occlusion_center", c);
    }

    private static ShaderMaterial PassFor(bool occluding)
    {
        if (occluding)
        {
            if (_occludingPass is null)
            {
                _occludingPass = NewPass();
                VisualSettings.Current.ApplyOcclusion(_occludingPass);
            }
            return _occludingPass;
        }
        return _pass ??= NewPass();
    }

    private static ShaderMaterial NewPass()
    {
        VisualSettings.OutlineSettings settings = VisualSettings.Current.Outline;
        var material = new ShaderMaterial { Shader = GD.Load<Shader>("res://src/View/Outline.gdshader") };
        material.SetShaderParameter("outline_color", new Color(settings.Color));
        material.SetShaderParameter("width_px", settings.WidthPx);
        material.SetShaderParameter("reference_height", settings.ReferenceHeight);
        return material;
    }
}
