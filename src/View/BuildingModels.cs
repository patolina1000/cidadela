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
            case "mana_tower":
                // Poste fino com um cristal azul-frio no alto (provisório; os fios vêm no feedback visual).
                Add(model, new CylinderMesh { TopRadius = 0.06f, BottomRadius = 0.1f, Height = 1.1f }, Palette.Wood.Darkened(0.3f), new Vector3(0f, 0.55f, 0f));
                Add(model, new SphereMesh { Radius = 0.13f, Height = 0.36f, RadialSegments = 6, Rings = 3 }, Palette.ManaBlue, new Vector3(0f, 1.25f, 0f));
                break;
            case "reliquary":
                // Altar baixo de pedra com o cristal puro que queima em cima.
                Add(model, new BoxMesh { Size = new Vector3(0.8f, 0.35f, 0.8f) }, Palette.Stone.Darkened(0.35f), new Vector3(0f, 0.175f, 0f));
                Add(model, new CylinderMesh { TopRadius = 0.3f, BottomRadius = 0.36f, Height = 0.15f }, Palette.Stone, new Vector3(0f, 0.42f, 0f));
                Add(model, new SphereMesh { Radius = 0.18f, Height = 0.5f, RadialSegments = 6, Rings = 3 }, Palette.ManaBlue, new Vector3(0f, 0.72f, 0f));
                break;
            case "crystal_mine":
                // Armação de madeira aberta em cima do veio (o veio aparece por baixo).
                foreach (float lx in new[] { -0.36f, 0.36f })
                foreach (float lz in new[] { -0.36f, 0.36f })
                    Add(model, new BoxMesh { Size = new Vector3(0.08f, 0.9f, 0.08f) }, Palette.Wood, new Vector3(lx, 0.45f, lz));
                Add(model, new BoxMesh { Size = new Vector3(0.84f, 0.08f, 0.84f) }, Palette.Wood.Darkened(0.3f), new Vector3(0f, 0.92f, 0f));
                Add(model, new BoxMesh { Size = new Vector3(0.06f, 0.5f, 0.06f) }, Palette.PurpleLichen, new Vector3(0f, 0.65f, 0f));
                break;
            case "well":
                Add(model, new CylinderMesh { TopRadius = 0.38f, BottomRadius = 0.4f, Height = 0.4f }, Palette.Stone, new Vector3(0f, 0.2f, 0f));
                Add(model, new CylinderMesh { TopRadius = 0.3f, BottomRadius = 0.3f, Height = 0.02f }, new Color("4F7C7A"), new Vector3(0f, 0.38f, 0f));
                Add(model, new BoxMesh { Size = new Vector3(0.9f, 0.06f, 0.06f) }, Palette.Wood, new Vector3(0f, 0.85f, 0f));
                foreach (float lx in new[] { -0.4f, 0.4f })
                    Add(model, new BoxMesh { Size = new Vector3(0.06f, 0.5f, 0.06f) }, Palette.Wood, new Vector3(lx, 0.6f, 0f));
                break;
            case "purifier":
                // Cuba de pedra com um cristal puro em cima.
                Add(model, new CylinderMesh { TopRadius = 0.42f, BottomRadius = 0.3f, Height = 0.5f }, Palette.Stone.Darkened(0.2f), new Vector3(0f, 0.25f, 0f));
                Add(model, new CylinderMesh { TopRadius = 0.36f, BottomRadius = 0.36f, Height = 0.02f }, new Color("4F7C7A"), new Vector3(0f, 0.5f, 0f));
                Add(model, new SphereMesh { Radius = 0.12f, Height = 0.34f, RadialSegments = 6, Rings = 3 }, Palette.ManaBlue, new Vector3(0f, 0.72f, 0f));
                break;
            case "mother_crystal":
                // Cristal alto azul-frio, provisório (D3 do Arthur).
                Add(model, new CylinderMesh { TopRadius = 0.0f, BottomRadius = 0.32f, Height = 2.2f, RadialSegments = 6 }, Palette.ManaBlue, new Vector3(0f, 1.1f, 0f));
                Add(model, new CylinderMesh { TopRadius = 0.0f, BottomRadius = 0.16f, Height = 1.0f, RadialSegments = 5 }, Palette.ManaBlue.Darkened(0.2f), new Vector3(0.3f, 0.5f, 0.1f));
                break;
            case "moth":
                // Pouso baixo com a seta da direção; a mariposa (pontinho de luz) é desenhada à parte pela WorldView.
                Add(model, new CylinderMesh { TopRadius = 0.18f, BottomRadius = 0.22f, Height = 0.12f, RadialSegments = 8 }, Palette.Stone.Darkened(0.3f), new Vector3(0f, 0.06f, 0f));
                AddOutputArrow(model);
                break;
            case "carrier_post":
                // Tablado com sacos e uma vara de carregar.
                Add(model, new BoxMesh { Size = new Vector3(0.8f, 0.1f, 0.8f) }, Palette.Wood, new Vector3(0f, 0.05f, 0f));
                Add(model, new SphereMesh { Radius = 0.18f, Height = 0.3f }, Palette.Wheat, new Vector3(-0.18f, 0.24f, 0.12f));
                Add(model, new SphereMesh { Radius = 0.15f, Height = 0.26f }, Palette.Wheat.Darkened(0.2f), new Vector3(0.16f, 0.22f, -0.1f));
                var pole = Add(model, new CylinderMesh { TopRadius = 0.025f, BottomRadius = 0.025f, Height = 0.9f }, Palette.Wood.Darkened(0.3f), new Vector3(0.28f, 0.5f, 0.24f));
                pole.Rotation = new Vector3(0.3f, 0f, 0.2f);
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
        var material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.9f };
        Outline.Attach(material);
        mesh.Material = material;
        var instance = new MeshInstance3D { Mesh = mesh, Position = position };
        parent.AddChild(instance);
        return instance;
    }
}
