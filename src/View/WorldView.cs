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
    private readonly Dictionary<ResourceNode, Node3D> _resourceNodes = new();
    private MeshInstance3D _hover = null!;
    private StandardMaterial3D _hoverMaterial = null!;
    private Node3D _castellanNode = null!;

    /// <summary>Nó desenhado do Castelão, para a câmera seguir.</summary>
    public Node3D CastellanNode => _castellanNode;

    public void Build(SimWorld world)
    {
        _world = world;
        BuildGround(world.Grid);

        foreach (ResourceNode resource in world.Resources)
        {
            var mesh = new BoxMesh { Size = new Vector3(0.8f, 0.8f, 0.8f) };
            _resourceNodes[resource] = AddShape($"Resource_{resource.Kind}_{resource.Id}", mesh,
                Palette.ForResource(resource.Kind), CellCenter(resource.Cell, 0.4f));
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

        _castellanNode = BuildCastellan();
        BuildHover();

        Render(0.0);
    }

    /// <summary>Atualiza o que muda, interpolando o que se move entre o tick anterior e o atual.</summary>
    public void Render(double alpha)
    {
        foreach ((ResourceNode resource, Node3D node) in _resourceNodes)
            node.Visible = !resource.IsDepleted;

        foreach ((Villager villager, Node3D node) in _villagerNodes)
        {
            System.Numerics.Vector2 p = System.Numerics.Vector2.Lerp(
                villager.PreviousPosition, villager.Position, (float)alpha);
            node.Position = new Vector3(p.X + 0.5f, 0.4f, p.Y + 0.5f);
        }

        Castellan castellan = _world.Castellan;
        System.Numerics.Vector2 c = System.Numerics.Vector2.Lerp(
            castellan.PreviousPosition, castellan.Position, (float)alpha);
        _castellanNode.Position = new Vector3(c.X + 0.5f, 0f, c.Y + 0.5f);
        // Basis.LookingAt olha para -Z; o "nariz" do Castelão fica em -Z local.
        var facing = new Vector3(castellan.Facing.X, 0f, castellan.Facing.Y);
        _castellanNode.Basis = Basis.LookingAt(facing, Vector3.Up);
    }

    /// <summary>
    /// Quadrado na célula sob o cursor: claro no alcance (mais forte sobre um recurso),
    /// vermelho fora do alcance; null esconde.
    /// </summary>
    public void ShowHover(GridPos? cell)
    {
        if (cell is not GridPos c || !_world.Grid.InBounds(c))
        {
            _hover.Visible = false;
            return;
        }

        _hover.Visible = true;
        _hover.Position = CellCenter(c, 0.02f);
        if (!_world.Castellan.CanReach(c))
            _hoverMaterial.AlbedoColor = Palette.Warning with { A = 0.45f };
        else if (_world.ResourceAt(c) is not null)
            _hoverMaterial.AlbedoColor = Palette.Bone with { A = 0.55f };
        else
            _hoverMaterial.AlbedoColor = Palette.Bone with { A = 0.25f };
    }

    private void BuildHover()
    {
        _hoverMaterial = new StandardMaterial3D
        {
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            AlbedoColor = Palette.Bone with { A = 0.25f },
        };
        var mesh = new PlaneMesh { Size = new Vector2(0.96f, 0.96f), Material = _hoverMaterial };
        _hover = new MeshInstance3D { Name = "HoverCell", Mesh = mesh, Visible = false };
        _hover.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        AddChild(_hover);
    }

    /// <summary>Cápsula maior e escura, com um "nariz" que mostra para onde está virado.</summary>
    private Node3D BuildCastellan()
    {
        var root = new Node3D { Name = "Castellan" };
        AddChild(root);

        var body = new CapsuleMesh { Radius = 0.3f, Height = 1.2f };
        body.Material = new StandardMaterial3D { AlbedoColor = Palette.DeepPurple, Roughness = 0.8f };
        root.AddChild(new MeshInstance3D { Name = "Body", Mesh = body, Position = new Vector3(0f, 0.6f, 0f) });

        var nose = new BoxMesh { Size = new Vector3(0.14f, 0.14f, 0.25f) };
        nose.Material = new StandardMaterial3D { AlbedoColor = Palette.Pumpkin, Roughness = 0.8f };
        root.AddChild(new MeshInstance3D { Name = "Nose", Mesh = nose, Position = new Vector3(0f, 0.9f, -0.35f) });

        return root;
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
