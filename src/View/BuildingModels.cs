using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Formas simples de cada construção (GDD, seção 17: silhueta própria para cada uma).
/// A raiz fica no chão, no centro da célula; o modelo filho gira para a direção.
/// </summary>
public static class BuildingModels
{
    public static Node3D Create(BuildingType type, Direction direction, GameData data)
    {
        var root = new Node3D();
        var model = new Node3D { Name = "Model", Rotation = new Vector3(0f, YawOf(direction), 0f) };
        root.AddChild(model);

        // Cabanas de trabalho: casinha com telhado da cor do recurso do ofício.
        if (type.Job is JobType job)
        {
            Add(model, new BoxMesh { Size = new Vector3(0.7f, 0.45f, 0.6f) }, Palette.Wood, new Vector3(0f, 0.225f, 0f));
            var roof = Add(model, new PrismMesh { Size = new Vector3(0.84f, 0.38f, 0.72f) },
                Palette.ForItem(data, job.Resource), new Vector3(0f, 0.64f, 0f));
            roof.Rotation = new Vector3(0f, Mathf.Pi / 2f, 0f);
            AddOutputArrow(model);
            return root;
        }

        switch (type.Kind)
        {
            case "belt":
                Add(model, new BoxMesh { Size = new Vector3(0.94f, 0.08f, 0.94f) }, Palette.Wood.Darkened(0.35f), new Vector3(0f, 0.04f, 0f));
                // Seta apontando para -Z local (a frente); o prisma deitado tem a ponta em -Z.
                Add(model, new BoxMesh { Size = new Vector3(0.12f, 0.03f, 0.34f) }, Palette.Wheat, new Vector3(0f, 0.095f, 0.12f));
                var head = Add(model, new PrismMesh { Size = new Vector3(0.38f, 0.26f, 0.03f) }, Palette.Wheat, new Vector3(0f, 0.095f, -0.16f));
                head.Rotation = new Vector3(-Mathf.Pi / 2f, 0f, 0f);
                break;
            case "chest":
                Add(model, new BoxMesh { Size = new Vector3(0.62f, 0.42f, 0.5f) }, Palette.Wood, new Vector3(0f, 0.21f, 0f));
                Add(model, new BoxMesh { Size = new Vector3(0.66f, 0.08f, 0.54f) }, Palette.Wheat, new Vector3(0f, 0.46f, 0f));
                break;
            case "sawmill":
                Add(model, new CylinderMesh { TopRadius = 0.42f, BottomRadius = 0.44f, Height = 0.5f }, Palette.Wood, new Vector3(0f, 0.25f, 0f));
                // A lâmina fica num pivô "Spin" que gira em volta de X quando a máquina trabalha.
                var spin = new Node3D { Name = "Spin", Position = new Vector3(0f, 0.62f, 0f) };
                model.AddChild(spin);
                var blade = Add(spin, new CylinderMesh { TopRadius = 0.3f, BottomRadius = 0.3f, Height = 0.05f }, Palette.Stone, Vector3.Zero);
                blade.Rotation = new Vector3(0f, 0f, Mathf.Pi / 2f);
                AddOutputArrow(model);
                break;
            case "smelter":
                Add(model, new CylinderMesh { TopRadius = 0.28f, BottomRadius = 0.4f, Height = 1.1f }, Palette.Stone, new Vector3(0f, 0.55f, 0f));
                Add(model, new CylinderMesh { TopRadius = 0.16f, BottomRadius = 0.16f, Height = 0.08f }, Palette.Pumpkin, new Vector3(0f, 1.12f, 0f));
                AddOutputArrow(model);
                break;
            case "forge":
                Add(model, new BoxMesh { Size = new Vector3(0.8f, 0.5f, 0.7f) }, Palette.Pumpkin, new Vector3(0f, 0.25f, 0f));
                Add(model, new CylinderMesh { TopRadius = 0.1f, BottomRadius = 0.13f, Height = 0.7f }, Palette.Midnight, new Vector3(0.22f, 0.85f, 0.15f));
                AddOutputArrow(model);
                break;
            default:
                Add(model, new BoxMesh { Size = new Vector3(0.8f, 0.8f, 0.8f) }, Colors.Magenta, new Vector3(0f, 0.4f, 0f));
                break;
        }
        return root;
    }

    /// <summary>Setinha no chão, na borda da frente: mostra por onde a máquina solta o que produz.</summary>
    private static void AddOutputArrow(Node3D model)
    {
        var head = Add(model, new PrismMesh { Size = new Vector3(0.3f, 0.18f, 0.03f) }, Palette.Wheat, new Vector3(0f, 0.03f, -0.44f));
        head.Rotation = new Vector3(-Mathf.Pi / 2f, 0f, 0f);
    }

    /// <summary>Yaw que leva a frente do modelo (-Z) para a direção.</summary>
    public static float YawOf(Direction direction) => -(int)direction * Mathf.Pi / 2f;

    /// <summary>Troca o material de todas as partes (usado na prévia fantasma).</summary>
    public static void OverrideMaterial(Node node, Material material)
    {
        if (node is MeshInstance3D mesh)
        {
            mesh.MaterialOverride = material;
            mesh.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        }
        foreach (Node child in node.GetChildren())
            OverrideMaterial(child, material);
    }

    private static MeshInstance3D Add(Node3D parent, PrimitiveMesh mesh, Color color, Vector3 position)
    {
        mesh.Material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.9f };
        var instance = new MeshInstance3D { Mesh = mesh, Position = position };
        parent.AddChild(instance);
        return instance;
    }
}
