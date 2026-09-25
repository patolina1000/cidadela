using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenha o <see cref="SimWorld"/> com formas simples. Só lê o estado.
/// A célula (x, z) ocupa o quadrado [x, x+1] × [z, z+1] no mundo 3D.
/// </summary>
public partial class WorldView : Node3D
{
    private const string GridShaderPath = "res://src/View/GridGround.gdshader";

    private SimWorld _world = null!;
    private readonly Dictionary<Villager, Node3D> _villagerNodes = new();

    public void Build(SimWorld world)
    {
        _world = world;
        BuildGround(world.Grid);

        foreach (ResourceNode resource in world.Resources)
        {
            var mesh = new BoxMesh { Size = new Vector3(0.8f, 0.8f, 0.8f) };
            AddShape($"Resource_{resource.Kind}_{resource.Id}", mesh, Palette.ForResource(resource.Kind),
                CellCenter(resource.Cell, 0.4f));
        }

        foreach (Machine machine in world.Machines)
        {
            var mesh = new CylinderMesh { TopRadius = 0.4f, BottomRadius = 0.4f, Height = 1.0f };
            AddShape($"Machine_{machine.Kind}_{machine.Id}", mesh, Palette.Pumpkin, CellCenter(machine.Cell, 0.5f));
        }

        foreach (Villager villager in world.Villagers)
        {
            var mesh = new CapsuleMesh { Radius = 0.2f, Height = 0.8f };
            _villagerNodes[villager] = AddShape($"Villager_{villager.Id}", mesh, Palette.Bone, Vector3.Zero);
        }

        Render(0.0);
    }

    /// <summary>Atualiza o que se move, interpolando entre o tick anterior e o atual.</summary>
    public void Render(double alpha)
    {
        foreach ((Villager villager, Node3D node) in _villagerNodes)
        {
            System.Numerics.Vector2 p = System.Numerics.Vector2.Lerp(
                villager.PreviousPosition, villager.Position, (float)alpha);
            node.Position = new Vector3(p.X + 0.5f, 0.4f, p.Y + 0.5f);
        }
    }

    private void BuildGround(WorldGrid grid)
    {
        var material = new ShaderMaterial { Shader = GD.Load<Shader>(GridShaderPath) };
        material.SetShaderParameter("base_color", Palette.Moss);
        material.SetShaderParameter("line_color", Palette.Moss.Darkened(0.25f));

        var ground = new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(grid.Width, grid.Height) },
            MaterialOverride = material,
            Position = new Vector3(grid.Width / 2f, 0f, grid.Height / 2f),
        };
        AddChild(ground);
    }

    private MeshInstance3D AddShape(string name, PrimitiveMesh mesh, Color color, Vector3 position)
    {
        mesh.Material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.9f };
        var node = new MeshInstance3D { Name = name, Mesh = mesh, Position = position };
        AddChild(node);
        return node;
    }

    private static Vector3 CellCenter(GridPos cell, float y) => new(cell.X + 0.5f, y, cell.Z + 0.5f);
}
