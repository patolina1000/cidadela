using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Feedback visual mínimo da linha da energia (docs/linha_energia.md), com formas provisórias: o estado de cada máquina
/// (problemas sempre; com Alt, todos), a barra de progresso da receita, os fios de luz azul-fria entre as torres (piscam
/// com a rede fraca) e a mariposa como um pontinho de luz batendo asas entre as duas células. Só lê a simulação.
/// </summary>
public partial class EnergyOverlay : Node3D
{
    private const float BadgeHeight = 1.55f;
    private const float BarHeight = 1.3f;
    private const float TowerTop = 1.25f;

    private SimWorld _world = null!;
    private int _buildingsVersion = -1;
    private int _manaRebuilds = -1;
    private float _time;
    private Shader _barShader = null!;

    private readonly Dictionary<Building, (Label3D Badge, MeshInstance3D Bar)> _machines = new();
    private readonly Dictionary<Building, MothVisual> _moths = new();
    private readonly List<(ManaNetwork Network, StandardMaterial3D Material)> _wireMaterials = new();
    private Node3D _wires = null!;

    /// <summary>Alt: todas as máquinas mostram o estado, não só as com problema.</summary>
    public bool InfoMode { get; set; }

    /// <summary>Estados e barras (a câmera cinematográfica esconde a interface; fios e mariposas ficam).</summary>
    public bool LabelsVisible { get; set; } = true;

    private sealed class MothVisual
    {
        public required Node3D Root { get; init; }
        public required MeshInstance3D Glow { get; init; }
        public required Node3D WingLeft { get; init; }
        public required Node3D WingRight { get; init; }
        public required MeshInstance3D Cargo { get; init; }
        public required StandardMaterial3D GlowMaterial { get; init; }
        public required StandardMaterial3D CargoMaterial { get; init; }
    }

    public void Build(SimWorld world)
    {
        _world = world;
        _barShader = GD.Load<Shader>("res://src/View/ProgressBar.gdshader");
        _wires = new Node3D { Name = "Wires" };
        AddChild(_wires);
    }

    public void Render(float dt)
    {
        _time += dt;
        if (_world.BuildingsVersion != _buildingsVersion)
            Sync();
        // As redes só existem depois do primeiro tick (e mudam junto com as construções): os fios seguem elas.
        if (_world.ManaRebuilds != _manaRebuilds)
            RebuildWires();
        foreach ((Building building, (Label3D badge, MeshInstance3D bar)) in _machines)
            RenderMachine(building, badge, bar);
        foreach ((Building building, MothVisual visual) in _moths)
            RenderMoth(building, visual);
        foreach ((ManaNetwork network, StandardMaterial3D material) in _wireMaterials)
        {
            // Rede fraca (falta mana, ou nada gera): o fio pisca.
            bool weak = network.Supply <= 0f || network.Supply < network.Demand;
            float glow = weak ? 0.35f + 0.65f * Mathf.Abs(Mathf.Sin(_time * 5f)) : 1f;
            material.AlbedoColor = new Color(Palette.ManaBlue, 0.85f * glow);
        }
    }

    /// <summary>Refaz tudo quando as construções mudam (e com elas as redes).</summary>
    private void Sync()
    {
        _buildingsVersion = _world.BuildingsVersion;
        foreach ((Label3D badge, MeshInstance3D bar) in _machines.Values)
        {
            badge.QueueFree();
            bar.QueueFree();
        }
        _machines.Clear();
        foreach (MothVisual moth in _moths.Values)
            moth.Root.QueueFree();
        _moths.Clear();

        foreach (Building building in _world.Buildings)
        {
            if (building.Machine is not null)
                _machines[building] = (NewBadge(building), NewBar(building));
            if (building.Moth is not null)
                _moths[building] = NewMoth(building);
        }
    }

    // ---- Máquinas ---------------------------------------------------------------------------------------------

    private Label3D NewBadge(Building building)
    {
        var badge = new Label3D
        {
            Name = $"Estado_{building.Id}",
            Billboard = BaseMaterial3D.BillboardModeEnum.Enabled,
            NoDepthTest = true,
            FontSize = 34,
            PixelSize = 0.006f,
            OutlineSize = 10,
            OutlineModulate = new Color(0f, 0f, 0f, 0.85f),
            Position = Center(building.Cell, BadgeHeight),
        };
        AddChild(badge);
        return badge;
    }

    private MeshInstance3D NewBar(Building building)
    {
        var bar = new MeshInstance3D
        {
            Name = $"Barra_{building.Id}",
            Mesh = new QuadMesh { Size = new Vector2(0.8f, 0.1f) },
            MaterialOverride = new ShaderMaterial { Shader = _barShader },
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            Position = Center(building.Cell, BarHeight),
        };
        AddChild(bar);
        return bar;
    }

    private void RenderMachine(Building building, Label3D badge, MeshInstance3D bar)
    {
        MachineState machine = building.Machine!;
        MachineWait? wait = machine.Waiting;
        badge.Text = StateText(_world.Data, building, machine, wait);
        badge.Modulate = wait is null ? Palette.Bone : Palette.Pumpkin;
        // Problema sempre aparece; trabalhando, só com Alt. Relicário vazio é problema (a rede fica sem geração).
        badge.Visible = LabelsVisible && (wait is not null || InfoMode);
        bar.Visible = LabelsVisible && (machine.IsWorking || InfoMode);
        bar.SetInstanceShaderParameter("progress", machine.Progress);
    }

    /// <summary>O estado curto da máquina, do jeito da especificação: trabalhando, falta insumo (qual), sem operador, sem mana, saída cheia.</summary>
    public static string StateText(GameData data, Building building, MachineState machine, MachineWait? wait) => wait switch
    {
        null => building.Type.Mana is { Supply: > 0f } ? "queimando" : building.Type.SpawnsVillager ? "formando aldeão" : "trabalhando",
        MachineWait.PostsEmpty => "sem operador",
        MachineWait.NoMana => "sem mana",
        MachineWait.OutputFull => "saída cheia",
        MachineWait.SourceDepleted => "veio esgotado",
        MachineWait.NoRoom => "sem espaço ao lado",
        _ => machine.MissingItem is string item ? $"falta {data.Item(item).Name.ToLowerInvariant()}" : "esperando",
    };

    // ---- Mariposas --------------------------------------------------------------------------------------------

    private MothVisual NewMoth(Building building)
    {
        var root = new Node3D { Name = $"Mariposa_{building.Id}", Position = Center(building.Cell, 0.5f) };
        AddChild(root);
        var glowMaterial = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            AlbedoColor = Palette.ManaBlue,
            EmissionEnabled = true,
            Emission = Palette.ManaBlue,
        };
        var glow = new MeshInstance3D
        {
            Mesh = new SphereMesh { Radius = 0.06f, Height = 0.12f, RadialSegments = 8, Rings = 4 },
            MaterialOverride = glowMaterial,
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
        };
        root.AddChild(glow);
        var wingMaterial = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            AlbedoColor = new Color(Palette.ManaBlue, 0.55f),
            CullMode = BaseMaterial3D.CullModeEnum.Disabled,
        };
        Node3D Wing(float side)
        {
            var pivot = new Node3D();
            root.AddChild(pivot);
            pivot.AddChild(new MeshInstance3D
            {
                Mesh = new QuadMesh { Size = new Vector2(0.16f, 0.1f), Orientation = PlaneMesh.OrientationEnum.Y },
                MaterialOverride = wingMaterial,
                Position = new Vector3(side * 0.09f, 0f, 0f),
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            });
            return pivot;
        }
        var cargoMaterial = new StandardMaterial3D { AlbedoColor = Palette.Bone };
        var cargo = new MeshInstance3D
        {
            Mesh = new BoxMesh { Size = new Vector3(0.1f, 0.1f, 0.1f) },
            MaterialOverride = cargoMaterial,
            Position = new Vector3(0f, -0.1f, 0f),
            Visible = false,
        };
        root.AddChild(cargo);
        return new MothVisual
        {
            Root = root, Glow = glow, WingLeft = Wing(-1f), WingRight = Wing(1f), Cargo = cargo,
            GlowMaterial = glowMaterial, CargoMaterial = cargoMaterial,
        };
    }

    private void RenderMoth(Building building, MothVisual visual)
    {
        MothState moth = building.Moth!;
        Vector3 here = Center(building.Cell, 0f);
        if (moth.Landed)
        {
            // Sem mana: pousada no pouso, apagada, asas fechadas.
            visual.Root.Position = here + new Vector3(0f, 0.16f, 0f);
            visual.WingLeft.Rotation = new Vector3(0f, 0f, -1.2f);
            visual.WingRight.Rotation = new Vector3(0f, 0f, 1.2f);
            visual.GlowMaterial.AlbedoColor = Palette.ManaBlue.Darkened(0.6f);
            visual.Cargo.Visible = moth.Carrying is not null;
            return;
        }
        visual.GlowMaterial.AlbedoColor = Palette.ManaBlue;
        GridPos fromCell = building.Cell.Step(building.Direction.Opposite(), moth.Type.Reach);
        GridPos toCell = building.Cell.Step(building.Direction, moth.Type.Reach);
        Vector3 position;
        if (moth.Carrying is string kind)
        {
            float t = moth.Progress;
            position = Center(fromCell, 0f).Lerp(Center(toCell, 0f), t) + new Vector3(0f, 0.45f + 0.35f * Mathf.Sin(Mathf.Pi * t), 0f);
            visual.Cargo.Visible = true;
            visual.CargoMaterial.AlbedoColor = Palette.ForItem(_world.Data, kind);
        }
        else
        {
            // Parada: paira sobre o pouso, balançando.
            position = here + new Vector3(0.08f * Mathf.Sin(_time * 1.7f + building.Id), 0.5f + 0.06f * Mathf.Sin(_time * 2.3f + building.Id), 0f);
            visual.Cargo.Visible = false;
        }
        visual.Root.Position = position;
        float flap = Mathf.Sin(_time * (moth.Flying ? 34f : 18f) + building.Id) * 0.9f;
        visual.WingLeft.Rotation = new Vector3(0f, 0f, flap);
        visual.WingRight.Rotation = new Vector3(0f, 0f, -flap);
    }

    // ---- Fios -------------------------------------------------------------------------------------------------

    /// <summary>Um fio por par de torres ligadas (as mesmas regras da simulação: distância real até o menor fio).</summary>
    private void RebuildWires()
    {
        _manaRebuilds = _world.ManaRebuilds;
        foreach (Node child in _wires.GetChildren())
            child.QueueFree();
        _wireMaterials.Clear();
        foreach (ManaNetwork network in _world.ManaNetworks)
        {
            var material = new StandardMaterial3D
            {
                ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
                Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
                AlbedoColor = new Color(Palette.ManaBlue, 0.85f),
            };
            _wireMaterials.Add((network, material));
            List<Building> towers = network.Towers;
            for (int i = 0; i < towers.Count; i++)
            for (int j = i + 1; j < towers.Count; j++)
            {
                Building a = towers[i], b = towers[j];
                float reach = Mathf.Min(a.Type.Tower!.Wire, b.Type.Tower!.Wire);
                float dx = a.Cell.X - b.Cell.X, dz = a.Cell.Z - b.Cell.Z;
                if (dx * dx + dz * dz <= reach * reach + 1e-4f)
                    _wires.AddChild(Wire(Center(a.Cell, TowerTop), Center(b.Cell, TowerTop), material));
            }
        }
    }

    private static MeshInstance3D Wire(Vector3 from, Vector3 to, Material material)
    {
        float length = from.DistanceTo(to);
        var wire = new MeshInstance3D
        {
            Mesh = new CylinderMesh { TopRadius = 0.035f, BottomRadius = 0.035f, Height = length, RadialSegments = 4, Rings = 1 },
            MaterialOverride = material,
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
        };
        // O cilindro fica em pé (Y); gira para o eixo do fio.
        Vector3 axis = (to - from).Normalized();
        wire.Basis = new Basis(new Quaternion(Vector3.Up, axis));
        wire.Position = (from + to) / 2f;
        return wire;
    }

    private static Vector3 Center(GridPos cell, float y) => new(cell.X + 0.5f, y, cell.Z + 0.5f);
}
