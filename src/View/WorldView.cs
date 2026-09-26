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
    private const string GroundShaderPath = "res://src/View/TerrainGround.gdshader";
    private const int TerrainTextureSize = 512;
    private const int GroundNoiseSize = 256;

    private SimWorld _world = null!;
    private readonly Dictionary<Villager, VillagerVisual> _villagerNodes = new();
    private readonly Dictionary<ResourceNode, ResourceVisual> _resourceVisuals = new();
    private readonly Dictionary<Building, Node3D> _buildingNodes = new();
    private readonly Dictionary<int, MeshInstance3D> _itemNodes = new();
    private readonly HashSet<int> _seenItems = new();
    private Label3D _chestLabel = null!;
    private readonly Dictionary<Building, Dictionary<string, int>> _chestSnapshots = new();
    private float _smokeTimer;
    private float _time;
    private int _buildingsVersion = -1;
    private Node3D? _ghost;
    private ShaderMaterial? _groundMaterial;
    private string? _ghostKind;
    private Direction _ghostDirection;
    private StandardMaterial3D _ghostMaterial = null!;
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
        BuildGround(world.Grid, world.Data);

        foreach (ResourceNode resource in world.Resources)
        {
            var root = new Node3D { Name = $"Resource_{resource.Kind}_{resource.Id}", Position = CellCenter(resource.Cell, 0f) };
            AddChild(root);
            var mesh = new BoxMesh { Size = new Vector3(0.8f, 0.8f, 0.8f) };
            mesh.Material = new StandardMaterial3D { AlbedoColor = Palette.ForItem(_world.Data, resource.Kind), Roughness = 0.9f };
            root.AddChild(new MeshInstance3D { Name = "Mesh", Mesh = mesh, Position = new Vector3(0f, 0.4f, 0f) });
            _resourceVisuals[resource] = new ResourceVisual { Root = root, LastRemaining = resource.Remaining };
        }


        foreach (Villager villager in world.Villagers)
        {
            var visual = new VillagerVisual { Name = $"Villager_{villager.Id}" };
            AddChild(visual);
            _villagerNodes[villager] = visual;
        }

        _castellan = new CastellanVisual { Name = "Castellan" };
        AddChild(_castellan);
        _effects = new Effects { Name = "Effects" };
        AddChild(_effects);
        BuildHover();
        _ghostMaterial = new StandardMaterial3D
        {
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
        };
        SyncBuildings(withEffects: false);
        _chestLabel = new Label3D
        {
            Name = "ChestInfo",
            Billboard = BaseMaterial3D.BillboardModeEnum.Enabled,
            NoDepthTest = true,
            FontSize = 40,
            PixelSize = 0.006f,
            OutlineSize = 10,
            Modulate = Palette.Bone,
            OutlineModulate = new Color(0f, 0f, 0f, 0.8f),
            Visible = false,
        };
        AddChild(_chestLabel);

        Render(0.0, 0.0);
    }

    /// <summary>Atualiza o que muda, interpolando o que se move entre o tick anterior e o atual.</summary>
    public void Render(double alpha, double delta)
    {
        float dt = (float)delta;
        foreach ((ResourceNode resource, ResourceVisual visual) in _resourceVisuals)
            RenderResource(resource, visual, dt);
        if (_world.BuildingsVersion != _buildingsVersion)
            SyncBuildings(withEffects: true);
        RenderBeltItems((float)alpha);
        RenderChestTakes();
        RenderMachines(dt);

        foreach ((Villager villager, VillagerVisual visual) in _villagerNodes)
            visual.UpdateFrom(villager, _world.Data, (float)alpha, dt);

        _castellan.UpdateFrom(_world.Castellan, (float)alpha, dt);
    }

    /// <summary>
    /// Deixa os nós iguais às construções da simulação. Construção nova "brota" com poeira e o custo
    /// saindo ("-4 Madeira"); construção tirada estoura e devolve o custo ("+4 Madeira").
    /// </summary>
    private void SyncBuildings(bool withEffects)
    {
        _buildingsVersion = _world.BuildingsVersion;
        var current = new HashSet<Building>(_world.Buildings);

        foreach (Building gone in new List<Building>(_buildingNodes.Keys))
        {
            if (current.Contains(gone))
                continue;
            Node3D node = _buildingNodes[gone];
            _buildingNodes.Remove(gone);
            _chestSnapshots.Remove(gone);
            if (withEffects)
                AnimateDeconstruct(gone, node);
            else
                node.QueueFree();
        }

        foreach (Building building in current)
        {
            if (_buildingNodes.ContainsKey(building))
                continue;
            Node3D node = BuildingModels.Create(building.Type, building.Direction, _world.Data);
            node.Name = $"Building_{building.Kind}_{building.Id}";
            node.Position = CellCenter(building.Cell, 0f);
            AddChild(node);
            _buildingNodes[building] = node;
            if (withEffects)
            {
                _effects.Burst(node.Position + new Vector3(0f, 0.1f, 0f), Palette.Wheat, amount: 12, speed: 2f);
                _effects.FloatingText(node.Position + new Vector3(0f, 1.1f, 0f), CostText(building.Type, "-"), Palette.Bone);
                node.Scale = new Vector3(0.3f, 0.3f, 0.3f);
                node.CreateTween().TweenProperty(node, "scale", Vector3.One, 0.35)
                    .SetTrans(Tween.TransitionType.Back).SetEase(Tween.EaseType.Out);
            }
        }
    }

    /// <summary>
    /// Um cubinho da cor do recurso por item em esteira, deslizando entre o tick anterior e o atual.
    /// Item que sumiu (entrou num baú ou voltou ao Castelão) tem o cubinho apagado.
    /// </summary>
    private void RenderBeltItems(float alpha)
    {
        _seenItems.Clear();
        foreach (BeltItem item in _world.BeltItems)
        {
            _seenItems.Add(item.Id);
            if (!_itemNodes.TryGetValue(item.Id, out MeshInstance3D? node))
            {
                var cube = new BoxMesh { Size = new Vector3(0.24f, 0.24f, 0.24f) };
                cube.Material = new StandardMaterial3D { AlbedoColor = Palette.ForItem(_world.Data, item.Kind), Roughness = 0.9f };
                node = new MeshInstance3D { Name = $"Item_{item.Id}", Mesh = cube };
                AddChild(node);
                _itemNodes[item.Id] = node;
            }
            System.Numerics.Vector2 p = System.Numerics.Vector2.Lerp(item.PreviousPosition, item.Position, alpha);
            node.Position = new Vector3(p.X + 0.5f, 0.22f, p.Y + 0.5f);
        }

        foreach (int id in new List<int>(_itemNodes.Keys))
        {
            if (_seenItems.Contains(id))
                continue;
            _itemNodes[id].QueueFree();
            _itemNodes.Remove(id);
        }
    }

    /// <summary>
    /// Quando um baú, a saída de uma máquina ou uma cabana perde itens (o Castelão recolheu), os itens
    /// voam até ele, como no desmontar. Compara com o que cada um tinha no frame anterior. Máquinas e
    /// cabanas que empurram para uma esteira também perdem itens, mas 1 por tick: só grupos de 2 ou mais
    /// contam como recolher.
    /// </summary>
    private void RenderChestTakes()
    {
        foreach (Building building in _buildingNodes.Keys)
        {
            if ((building.Storage ?? building.Machine?.Output ?? building.Workplace?.Stored) is not Inventory storage)
                continue;
            if (!_chestSnapshots.TryGetValue(building, out Dictionary<string, int>? before))
            {
                _chestSnapshots[building] = new Dictionary<string, int>(storage.Counts);
                continue;
            }

            double delay = 0;
            Vector3 from = CellCenter(building.Cell, 0.5f);
            foreach ((string kind, int had) in before)
            {
                int taken = had - storage.Count(kind);
                if (building.Storage is null && taken < 2)
                    continue;
                for (int i = 0; i < System.Math.Min(taken, 6); i++)
                {
                    _effects.FlyTo(from, _castellan, Palette.ForItem(_world.Data, kind), delay);
                    delay += 0.05;
                }
            }
            _chestSnapshots[building] = new Dictionary<string, int>(storage.Counts);
        }
    }

    /// <summary>
    /// Máquina trabalhando mostra que está viva (GDD, seção 17: "estado visível"): a serraria gira a lâmina,
    /// as outras pulsam e soltam fumaça. Parada, fica imóvel.
    /// </summary>
    private void RenderMachines(float dt)
    {
        _time += dt;
        _smokeTimer -= dt;
        bool puff = _smokeTimer <= 0f;
        if (puff)
            _smokeTimer = 0.45f;

        foreach ((Building building, Node3D node) in _buildingNodes)
        {
            if (building.Machine is not MachineState machine)
                continue;
            var model = node.GetNode<Node3D>("Model");
            if (model.GetNodeOrNull<Node3D>("Spin") is Node3D spin && machine.IsWorking)
                spin.Rotation = new Vector3(spin.Rotation.X + dt * 12f, 0f, 0f);

            float pulse = machine.IsWorking ? 1f + 0.04f * Mathf.Sin(_time * 10f) : 1f;
            model.Scale = new Vector3(1f, pulse, 1f);

            if (puff && machine.IsWorking && building.Kind != "sawmill")
                _effects.Smoke(node.Position + new Vector3(0f, 1.15f, 0f));
        }
    }

    /// <summary>
    /// Etiqueta sobre a construção sob o cursor: o que um baú guarda, ou receita e estado de uma máquina.
    /// null (ou célula sem baú/máquina) esconde.
    /// </summary>
    public void ShowBuildingInfo(GridPos? cell)
    {
        Building? building = cell is GridPos c ? _world.BuildingAt(c) : null;
        List<string>? lines = building switch
        {
            { Storage: Inventory storage } => ChestLines(building, storage),
            { Machine: MachineState machine } => MachineLines(building, machine),
            { Workplace: Workplace work } => WorkplaceLines(building, work),
            _ => null,
        };
        if (building is null || lines is null)
        {
            _chestLabel.Visible = false;
            return;
        }

        _chestLabel.Text = string.Join("\n", lines);
        _chestLabel.Position = CellCenter(building.Cell, building.Machine is not null ? 1.9f : 1.3f);
        _chestLabel.Visible = true;
    }

    private List<string> ChestLines(Building chest, Inventory storage)
    {
        var lines = new List<string> { chest.Type.Name };
        lines.AddRange(Contents(storage));
        if (lines.Count == 1)
            lines.Add("vazio");
        return lines;
    }

    private List<string> MachineLines(Building building, MachineState machine)
    {
        RecipeType recipe = machine.Recipe;
        var lines = new List<string>
        {
            building.Type.Name,
            $"{ItemsText(recipe.Inputs)} → {ItemsText(recipe.Outputs)} ({recipe.Ticks / (float)SimClock.TicksPerSecond:0.#} s)",
        };
        if (!machine.Input.IsEmpty)
            lines.Add("Entrada: " + string.Join(", ", Contents(machine.Input)));
        if (!machine.Output.IsEmpty)
            lines.Add("Pronto: " + string.Join(", ", Contents(machine.Output)));
        lines.Add(machine.Waiting switch
        {
            null => $"Trabalhando {machine.Progress:P0}",
            MachineWait.OutputFull => "Parada: saída cheia",
            _ => "Esperando " + ItemsText(recipe.Inputs),
        });
        return lines;
    }

    /// <summary>
    /// O que dá para focar perto de um ponto do chão: Castelão ou aldeão a menos de ~1 célula,
    /// senão a construção ou o recurso da célula. null se não há nada.
    /// </summary>
    public FocusTarget? FindFocus(Vector3 ground)
    {
        var flat = new Vector2(ground.X, ground.Z);
        Node3D? nearest = null;
        float best = 0.9f;
        foreach (Node3D node in AnimatedNodes())
        {
            float d = new Vector2(node.Position.X, node.Position.Z).DistanceTo(flat);
            if (d < best)
            {
                best = d;
                nearest = node;
            }
        }
        if (nearest == _castellan)
            return new FocusTarget(_castellan, 0.8f, 3.2f, DescribeCastellan);
        foreach ((Villager villager, VillagerVisual visual) in _villagerNodes)
            if (visual == nearest)
                return new FocusTarget(visual, 0.55f, 2.6f, () => DescribeVillager(villager));

        var cell = new GridPos(Mathf.FloorToInt(ground.X), Mathf.FloorToInt(ground.Z));
        if (_world.BuildingAt(cell) is Building building && _buildingNodes.TryGetValue(building, out Node3D? bNode))
        {
            float height = building.Type.IsBelt ? 0.15f : 0.6f;
            return new FocusTarget(bNode, height, building.Type.IsBelt ? 2.2f : 3.4f,
                () => string.Join("  —  ", ShowableLines(building)));
        }
        if (_world.ResourceAt(cell) is ResourceNode resource && _resourceVisuals.TryGetValue(resource, out ResourceVisual? rv))
            return new FocusTarget(rv.Root, 0.4f, 3f, () => $"{resource.Type.Name}  —  restam {resource.Remaining}");
        return null;
    }

    /// <summary>O Castelão como alvo padrão da câmera cinematográfica.</summary>
    public FocusTarget CastellanFocus() => new(_castellan, 0.8f, 3.2f, DescribeCastellan);

    private IEnumerable<Node3D> AnimatedNodes()
    {
        yield return _castellan;
        foreach (VillagerVisual visual in _villagerNodes.Values)
            yield return visual;
    }

    private string DescribeCastellan()
    {
        Castellan c = _world.Castellan;
        return c.GatherTarget is ResourceNode node
            ? $"Castelão  —  coletando {node.Type.Name} {c.GatherProgress:P0}"
            : "Castelão";
    }

    private string DescribeVillager(Villager villager)
    {
        if (villager.Home?.Workplace is not Workplace work)
            return "Aldeão  —  sem ofício";
        return $"Aldeão {work.Job.Name}  —  {VillagerTaskText(villager, work)}";
    }

    private List<string> ShowableLines(Building building) => building switch
    {
        { Storage: Inventory storage } => ChestLines(building, storage),
        { Machine: MachineState machine } => MachineLines(building, machine),
        { Workplace: Workplace work } => WorkplaceLines(building, work),
        _ => new List<string> { building.Type.Name },
    };

    private string VillagerTaskText(Villager worker, Workplace work)
    {
        string resource = _world.Data.Item(work.Job.Resource).Name;
        return worker.Task switch
        {
            VillagerTask.GoingToResource => $"indo buscar {resource}",
            VillagerTask.Gathering => $"coletando ({worker.CarryingCount}/{worker.Stats.Carry})",
            VillagerTask.ReturningHome => $"levando {worker.CarryingCount} {resource}",
            _ when work.Free <= 0 => "parado: cabana cheia",
            _ => $"parado: sem {resource} no raio de {work.Job.Radius:0} células",
        };
    }

    private List<string> WorkplaceLines(Building building, Workplace work)
    {
        string resource = _world.Data.Item(work.Job.Resource).Name;
        var lines = new List<string>
        {
            building.Type.Name,
            $"Guardado: {work.Stored.Count(work.Job.Resource)}/{work.Job.Capacity} {resource}",
        };
        if (work.Worker is not Villager worker)
        {
            lines.Add("Sem trabalhador: nenhum aldeão livre");
            return lines;
        }
        lines.Add($"{work.Job.Name}: {VillagerTaskText(worker, work)}");
        return lines;
    }

    private IEnumerable<string> Contents(Inventory inventory)
    {
        foreach (ItemType type in _world.Data.Items)
            if (inventory.Count(type.Kind) > 0)
                yield return $"{type.Name}: {inventory.Count(type.Kind)}";
    }

    private string ItemsText(IReadOnlyDictionary<string, int> items)
    {
        var parts = new List<string>();
        foreach ((string kind, int amount) in items)
            parts.Add($"{amount} {_world.Data.Item(kind).Name}");
        return string.Join(" + ", parts);
    }

    /// <summary>
    /// Desmontar: sacode (achata e volta), encolhe para dentro do chão e estoura em poeira;
    /// os itens devolvidos voam em arco até o Castelão, um cubinho da cor de cada recurso.
    /// </summary>
    private void AnimateDeconstruct(Building building, Node3D node)
    {
        Vector3 center = node.Position + new Vector3(0f, 0.35f, 0f);
        _effects.FloatingText(node.Position + new Vector3(0f, 1.1f, 0f), CostText(building.Type, "+"), Palette.Bone);

        Tween tween = node.CreateTween();
        tween.TweenProperty(node, "scale", new Vector3(1.2f, 0.75f, 1.2f), 0.07);
        tween.TweenProperty(node, "scale", new Vector3(0.9f, 1.15f, 0.9f), 0.07);
        tween.TweenProperty(node, "scale", Vector3.Zero, 0.22)
            .SetTrans(Tween.TransitionType.Back).SetEase(Tween.EaseType.In);
        tween.TweenCallback(Callable.From(() =>
        {
            _effects.Burst(center, Palette.Wheat, amount: 14, speed: 2.5f);
            node.QueueFree();
        }));

        // Até 4 cubinhos por recurso, em sequência, para dar a ideia da quantidade sem virar enxame.
        double delay = 0.25;
        foreach ((string item, int amount) in building.Type.Cost)
        {
            for (int i = 0; i < System.Math.Min(amount, 4); i++)
            {
                _effects.FlyTo(center, _castellan, Palette.ForItem(_world.Data, item), delay);
                delay += 0.06;
            }
        }
    }

    private string CostText(BuildingType type, string sign)
    {
        var parts = new List<string>();
        foreach ((string item, int amount) in type.Cost)
            parts.Add($"{sign}{amount} {_world.Data.Item(item).Name}");
        return string.Join("  ", parts);
    }

    /// <summary>
    /// Prévia translúcida da construção escolhida na célula do cursor: verde se dá para construir,
    /// vermelha se não. null em qualquer argumento esconde.
    /// </summary>
    public void ShowGhost(BuildingType? type, GridPos? cell, Direction direction)
    {
        // A grade do chão só aparece com uma construção escolhida (GDD, seção 17).
        _groundMaterial?.SetShaderParameter("grid_strength", type is null ? 0f : 1f);

        if (type is null || cell is not GridPos c || !_world.Grid.InBounds(c))
        {
            if (_ghost is not null)
                _ghost.Visible = false;
            return;
        }

        if (_ghost is null || _ghostKind != type.Kind || _ghostDirection != direction)
        {
            _ghost?.QueueFree();
            _ghost = BuildingModels.Create(type, direction, _world.Data);
            _ghost.Name = "Ghost";
            BuildingModels.OverrideMaterial(_ghost, _ghostMaterial);
            AddChild(_ghost);
            _ghostKind = type.Kind;
            _ghostDirection = direction;
        }

        _ghost.Visible = true;
        _ghost.Position = CellCenter(c, 0.01f);
        bool ok = _world.CanBuild(type, c) == BuildCheck.Ok;
        _ghostMaterial.AlbedoColor = (ok ? Palette.Sickly : Palette.Warning) with { A = 0.5f };
    }

    /// <summary>
    /// Encolhe conforme esgota; a cada item tirado, sacode e solta lascas e "+1"; ao esgotar, estoura.
    /// </summary>
    private void RenderResource(ResourceNode resource, ResourceVisual visual, float dt)
    {
        if (!visual.Root.Visible)
            return;

        Color color = Palette.ForItem(_world.Data, resource.Kind);
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

    private void BuildGround(WorldGrid grid, GameData data)
    {
        // Um pixel por célula com o índice do terreno; o shader lê sem filtro.
        Image map = Image.CreateEmpty(grid.Width, grid.Height, false, Image.Format.R8);
        for (int z = 0; z < grid.Height; z++)
            for (int x = 0; x < grid.Width; x++)
                map.SetPixel(x, z, new Color(grid.TerrainAt(new GridPos(x, z)) / 255f, 0f, 0f));

        var layers = new Godot.Collections.Array<Image>();
        foreach (TerrainType terrain in data.Terrains)
            layers.Add(TerrainLayer(terrain));
        var textures = new Texture2DArray();
        textures.CreateFromImages(layers);

        var noise = new NoiseTexture2D
        {
            Width = GroundNoiseSize,
            Height = GroundNoiseSize,
            Seamless = true,
            Noise = new FastNoiseLite { NoiseType = FastNoiseLite.NoiseTypeEnum.SimplexSmooth, Frequency = 0.02f, Seed = 7 },
        };

        _groundMaterial = new ShaderMaterial { Shader = GD.Load<Shader>(GroundShaderPath) };
        _groundMaterial.SetShaderParameter("terrain_textures", textures);
        _groundMaterial.SetShaderParameter("terrain_map", ImageTexture.CreateFromImage(map));
        _groundMaterial.SetShaderParameter("noise", noise);
        _groundMaterial.SetShaderParameter("map_size", new Vector2(grid.Width, grid.Height));

        var ground = new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(grid.Width, grid.Height) },
            MaterialOverride = _groundMaterial,
            Position = new Vector3(grid.Width / 2f, 0f, grid.Height / 2f),
        };
        AddChild(ground);
    }

    /// <summary>
    /// Textura de um terreno como camada da pilha: todas no mesmo tamanho e formato, com mipmaps.
    /// Sem textura (ou arquivo faltando), vira uma cor lisa de musgo.
    /// </summary>
    private static Image TerrainLayer(TerrainType terrain)
    {
        Image? image = !string.IsNullOrEmpty(terrain.Texture) && ResourceLoader.Exists(terrain.Texture)
            ? GD.Load<Texture2D>(terrain.Texture).GetImage()
            : null;
        if (image is null)
        {
            GD.PushWarning($"Terreno \"{terrain.Kind}\" sem textura; usando cor lisa.");
            image = Image.CreateEmpty(TerrainTextureSize, TerrainTextureSize, false, Image.Format.Rgba8);
            image.Fill(Palette.Moss);
        }
        if (image.IsCompressed())
            image.Decompress();
        image.ClearMipmaps();
        image.Convert(Image.Format.Rgba8);
        if (image.GetWidth() != TerrainTextureSize || image.GetHeight() != TerrainTextureSize)
            image.Resize(TerrainTextureSize, TerrainTextureSize, Image.Interpolation.Lanczos);
        image.GenerateMipmaps();
        return image;
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
