using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenha o <see cref="SimWorld"/> com formas simples. Só lê o estado; os efeitos
/// (lascas, "+1", sacudidas) nascem de comparar o estado com o do frame anterior.
/// A célula (x, z) ocupa o quadrado [x, x+1] × [z, z+1] no mundo 3D.
/// </summary>
public partial class WorldView : Node3D
{
    private const string GridShaderPath = "res://src/View/GridGround.gdshader";

    private SimWorld _world = null!;
    private readonly Dictionary<Villager, Node3D> _villagerNodes = new();
    private readonly Dictionary<ResourceNode, ResourceVisual> _resourceVisuals = new();
    private MeshInstance3D _hover = null!;
    private StandardMaterial3D _hoverMaterial = null!;
    private CastellanVisual _castellan = null!;
    private Effects _effects = null!;

    /// <summary>Nó desenhado do Castelão, para a câmera seguir.</summary>
    public Node3D CastellanNode => _castellan;

    /// <summary>Recurso desenhado: raiz no chão (escalar não tira o cubo do chão) e último restante visto.</summary>
    private sealed class ResourceVisual
    {
        public required Node3D Root { get; init; }
        public int LastRemaining { get; set; }
        public float Punch { get; set; }
    }

    public void Build(SimWorld world)
    {
        _world = world;
        BuildGround(world.Grid);

        foreach (ResourceNode resource in world.Resources)
        {
            var root = new Node3D { Name = $"Resource_{resource.Kind}_{resource.Id}", Position = CellCenter(resource.Cell, 0f) };
            AddChild(root);
            var mesh = new BoxMesh { Size = new Vector3(0.8f, 0.8f, 0.8f) };
            mesh.Material = new StandardMaterial3D { AlbedoColor = Palette.ForResource(resource.Kind), Roughness = 0.9f };
            root.AddChild(new MeshInstance3D { Name = "Mesh", Mesh = mesh, Position = new Vector3(0f, 0.4f, 0f) });
            _resourceVisuals[resource] = new ResourceVisual { Root = root, LastRemaining = resource.Remaining };
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

        _castellan = new CastellanVisual { Name = "Castellan" };
        AddChild(_castellan);
        _effects = new Effects { Name = "Effects" };
        AddChild(_effects);
        BuildHover();

        Render(0.0, 0.0);
    }

    /// <summary>Atualiza o que muda, interpolando o que se move entre o tick anterior e o atual.</summary>
    public void Render(double alpha, double delta)
    {
        float dt = (float)delta;
        foreach ((ResourceNode resource, ResourceVisual visual) in _resourceVisuals)
            RenderResource(resource, visual, dt);

        foreach ((Villager villager, Node3D node) in _villagerNodes)
        {
            System.Numerics.Vector2 p = System.Numerics.Vector2.Lerp(
                villager.PreviousPosition, villager.Position, (float)alpha);
            node.Position = new Vector3(p.X + 0.5f, 0.4f, p.Y + 0.5f);
        }

        _castellan.UpdateFrom(_world.Castellan, (float)alpha, dt);
    }

    /// <summary>
    /// Encolhe conforme esgota; a cada item tirado, sacode e solta lascas e "+1"; ao esgotar, estoura.
    /// </summary>
    private void RenderResource(ResourceNode resource, ResourceVisual visual, float dt)
    {
        if (!visual.Root.Visible)
            return;

        Color color = Palette.ForResource(resource.Kind);
        Vector3 top = visual.Root.Position + new Vector3(0f, 0.8f, 0f);
        if (resource.Remaining < visual.LastRemaining)
        {
            int taken = visual.LastRemaining - resource.Remaining;
            visual.LastRemaining = resource.Remaining;
            visual.Punch = 1f;
            _effects.Burst(top, color, amount: 8);
            _effects.FloatingText(top + new Vector3(0f, 0.3f, 0f), $"+{taken} {resource.Type.Name}", Palette.Bone);
        }

        if (resource.IsDepleted)
        {
            _effects.Burst(visual.Root.Position + new Vector3(0f, 0.4f, 0f), color, amount: 24, speed: 3.5f);
            visual.Root.Visible = false;
            return;
        }

        // Nunca menor que 55%: ainda precisa ser clicável e reconhecível.
        float size = Mathf.Lerp(0.55f, 1f, (float)resource.Remaining / resource.Type.StartAmount);
        visual.Punch = Mathf.Lerp(visual.Punch, 0f, 1f - Mathf.Exp(-14f * dt));
        float squash = 0.22f * visual.Punch;
        visual.Root.Scale = new Vector3(size * (1f + squash), size * (1f - squash), size * (1f + squash));
    }

    /// <summary>
    /// Quadrado na célula sob o cursor: forte sobre um recurso que dá para coletar daqui,
    /// claro numa célula no alcance de construir, vermelho sobre recurso longe ou fora do alcance;
    /// null esconde.
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
        Castellan castellan = _world.Castellan;
        if (_world.ResourceAt(c) is not null)
            _hoverMaterial.AlbedoColor = castellan.CanGather(c)
                ? Palette.Bone with { A = 0.55f }
                : Palette.Warning with { A = 0.45f };
        else if (castellan.CanReach(c))
            _hoverMaterial.AlbedoColor = Palette.Bone with { A = 0.25f };
        else
            _hoverMaterial.AlbedoColor = Palette.Warning with { A = 0.45f };
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
