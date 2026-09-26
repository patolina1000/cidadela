using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Desenho de um aldeão: cápsula clara com chapéu da cor do ofício (sem ofício, sem chapéu) e,
/// quando carrega algo, um cubinho da cor do item nas costas. Vira suave, quica ao andar e dá o
/// mesmo golpe do Castelão ao coletar.
/// </summary>
public partial class VillagerVisual : Node3D
{
    private const float TurnSmoothing = 12f;
    private const float SwingSmoothing = 30f;

    private Node3D _pivot = null!;
    private MeshInstance3D _hat = null!;
    private StandardMaterial3D _hatMaterial = null!;
    private MeshInstance3D _load = null!;
    private StandardMaterial3D _loadMaterial = null!;
    private float _yaw;
    private float _swing;
    private float _bobPhase;
    private System.Numerics.Vector2 _lastDrawn;
    private bool _hasLast;

    public override void _Ready()
    {
        _pivot = new Node3D { Name = "Pivot" };
        AddChild(_pivot);

        var body = new CapsuleMesh { Radius = 0.2f, Height = 0.8f };
        body.Material = new StandardMaterial3D { AlbedoColor = Palette.Bone, Roughness = 0.9f };
        _pivot.AddChild(new MeshInstance3D { Name = "Body", Mesh = body, Position = new Vector3(0f, 0.4f, 0f) });

        _hatMaterial = new StandardMaterial3D { Roughness = 0.9f };
        var hat = new CylinderMesh { TopRadius = 0.08f, BottomRadius = 0.2f, Height = 0.16f, Material = _hatMaterial };
        _hat = new MeshInstance3D { Name = "Hat", Mesh = hat, Position = new Vector3(0f, 0.86f, 0f), Visible = false };
        _pivot.AddChild(_hat);

        _loadMaterial = new StandardMaterial3D { Roughness = 0.9f };
        var load = new BoxMesh { Size = new Vector3(0.22f, 0.22f, 0.22f), Material = _loadMaterial };
        // Nas costas: +Z local (a frente é -Z).
        _load = new MeshInstance3D { Name = "Load", Mesh = load, Position = new Vector3(0f, 0.5f, 0.24f), Visible = false };
        _pivot.AddChild(_load);
    }

    public void UpdateFrom(Villager villager, GameData data, float alpha, float dt)
    {
        System.Numerics.Vector2 p = System.Numerics.Vector2.Lerp(villager.PreviousPosition, villager.Position, alpha);
        Position = new Vector3(p.X + 0.5f, 0f, p.Y + 0.5f);

        float targetYaw = Mathf.Atan2(-villager.Facing.X, -villager.Facing.Y);
        _yaw = Mathf.LerpAngle(_yaw, targetYaw, 1f - Mathf.Exp(-TurnSmoothing * dt));
        Rotation = new Vector3(0f, _yaw, 0f);

        float walked = _hasLast ? System.Numerics.Vector2.Distance(_lastDrawn, p) : 0f;
        _lastDrawn = p;
        _hasLast = true;
        _bobPhase += walked * 1.4f * Mathf.Pi;
        float bob = walked > 0.0001f ? Mathf.Abs(Mathf.Sin(_bobPhase)) * 0.07f : 0f;

        if (villager.Home?.Workplace is Workplace work)
        {
            _hat.Visible = true;
            _hatMaterial.AlbedoColor = Palette.ForItem(data, work.Job.Resource);
        }
        else
        {
            _hat.Visible = false;
        }

        _load.Visible = villager.CarryingCount > 0 && villager.CarryingKind is not null;
        if (villager.CarryingKind is string kind)
            _loadMaterial.AlbedoColor = Palette.ForItem(data, kind);

        float targetSwing = 0f;
        if (villager.Task == VillagerTask.Gathering && villager.Target is ResourceNode node)
        {
            float step = 1f / Mathf.Max(1f, node.Type.GatherTicks * villager.Stats.GatherMultiplier);
            targetSwing = CastellanVisual.SwingAngle(Mathf.Clamp(villager.GatherProgress + alpha * step, 0f, 1f));
        }
        _swing = Mathf.Lerp(_swing, targetSwing, 1f - Mathf.Exp(-SwingSmoothing * dt));

        _pivot.Position = new Vector3(0f, bob, 0f);
        _pivot.Rotation = new Vector3(Mathf.DegToRad(_swing), 0f, 0f);
    }
}
