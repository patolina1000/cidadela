using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Formas provisórias dos recursos, nas medidas da proposta do CENÁRIO (até os modelos dele entrarem): árvore de
/// 2,4 m (tronco até 1,2 m e copa redonda a partir de 1 m), pedra de 0,45 m e veio de 0,4 m, todos numa célula.
/// Material toon com a borda de luz fria (data/visual.json), um por cor e compartilhado entre todos os recursos.
/// </summary>
public static class ResourceModels
{
    private static readonly Dictionary<Color, ShaderMaterial> Materials = new();

    /// <summary>Altura do topo, para os efeitos de coleta nascerem em cima do recurso.</summary>
    public static float HeightOf(string kind) => kind switch
    {
        "wood" => 2.4f,
        "stone" => 0.45f,
        _ => 0.4f,
    };

    public static Node3D Create(string kind, GameData data)
    {
        var model = new Node3D { Name = "Mesh" };
        Color color = Palette.ForItem(data, kind);
        switch (kind)
        {
            case "wood":
                Add(model, new CylinderMesh { TopRadius = 0.08f, BottomRadius = 0.12f, Height = 1.2f }, color, new Vector3(0f, 0.6f, 0f));
                Add(model, new SphereMesh { Radius = 0.55f, Height = 1.4f, RadialSegments = 16, Rings = 8 }, Palette.GrayMoss, new Vector3(0f, 1.7f, 0f));
                break;
            default:
                float height = HeightOf(kind);
                Add(model, new SphereMesh { Radius = 0.4f, Height = height * 2f, RadialSegments = 12, Rings = 6 }, color, Vector3.Zero);
                break;
        }
        return model;
    }

    private static void Add(Node3D parent, PrimitiveMesh mesh, Color color, Vector3 position)
    {
        mesh.Material = MaterialFor(color);
        parent.AddChild(new MeshInstance3D { Mesh = mesh, Position = position });
    }

    public static ShaderMaterial MaterialFor(Color color)
    {
        if (Materials.TryGetValue(color, out ShaderMaterial? material))
            return material;
        material = new ShaderMaterial { Shader = GD.Load<Shader>(VillagerLooks.ToonShaderPath) };
        material.SetShaderParameter("albedo", color);
        VisualSettings.Current.ApplyRim(material);
        Materials[color] = material;
        return material;
    }
}
