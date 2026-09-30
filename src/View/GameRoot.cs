using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Liga a simulação à cena: carrega os dados e o mapa, transforma a entrada do jogador
/// em comandos, avança o <see cref="SimClock"/> a cada frame, roda os ticks e pede para a
/// <see cref="WorldView"/> desenhar.
/// WASD move o Castelão (ela só corre; não há andar nem botão de correr).
/// Mouse: esquerdo coleta, recolhe de um baú, constrói (com uma construção escolhida) ou põe o item da mão
/// numa esteira ou baú (com um item segurado); segurar e arrastar repete célula a célula.
/// Direito sem arrastar solta o que está escolhido ou desmonta. Teclado: WASD anda, 1–9 escolhem, R gira, Esc solta (sem nada na mão, abre o menu de pausa),
/// C entra/sai da câmera cinematográfica no que está sob o cursor (ou no Castelão).
/// O liga e desliga o contorno fino escuro (prova, 29/09/2026). H desenha no chão as formas de colisão.
/// Segurar Alt (modo de informação) mostra o ícone de estado de todos os aldeões; sem Alt, só dos que têm problema.
/// Depuração da protagonista (temporária): [ e ] baixam e sobem a velocidade dela em 0,1 cél/s, mostrada no HUD.
/// Depuração dos aldeões: V alterna o patamar de velocidade, B liga/desliga a penalidade (fome ou moral baixa).
/// Pausa (GDD, seção 3): Espaço pausa e continua. Na pausa a câmera continua livre, mas nada que muda o mundo é
/// aceito. Não há velocidade 1x/2x/3x (decisão do Arthur, 29/09/2026: como no Factorio).
/// </summary>
public partial class GameRoot : Node3D
{
    [Export(PropertyHint.File, "*.json")] public string MapPath = "res://data/maps/mapa_teste.json";
    [Export(PropertyHint.File, "*.json")] public string ItemsPath = "res://data/items.json";
    [Export(PropertyHint.File, "*.json")] public string ResourcesPath = "res://data/resources.json";
    [Export(PropertyHint.File, "*.json")] public string CastellanPath = "res://data/castellan.json";
    [Export(PropertyHint.File, "*.json")] public string VillagersPath = "res://data/villagers.json";
    [Export(PropertyHint.File, "*.json")] public string BuildingsPath = "res://data/buildings.json";
    [Export(PropertyHint.File, "*.json")] public string RecipesPath = "res://data/recipes.json";
    [Export(PropertyHint.File, "*.json")] public string TerrainPath = "res://data/terrain.json";

    private SimWorld _world = null!;
    private readonly SimClock _clock = new();
    private WorldView _view = null!;
    private CameraRig _camera = null!;
    private Hotbar _hotbar = null!;
    private Label _manaLabel = null!;
    private VillagerPanel _villagerPanel = null!;
    /// <summary>As construções da barra (as de data/buildings.json com "hotbar" ligado), na ordem das teclas.</summary>
    private readonly List<BuildingType> _hotbarTypes = new();
    private InventoryBar _inventoryBar = null!;
    private CinematicOverlay _cinematicOverlay = null!;
    private FocusTarget? _focus;
    private Label _debugLabel = null!;
    private PerfOverlay _perf = null!;
    private Label _inventoryLabel = null!;
    private Label _pauseLabel = null!;
    private PauseMenu _pauseMenu = null!;

    // Modo de construção: o que está escolhido, para onde aponta e a última célula do arrasto.
    private BuildingType? _selected;
    private string? _heldItem;
    private Direction _buildDirection = Direction.North;
    private bool _leftHeld;
    private GridPos? _lastBuildCell;

    private System.Numerics.Vector2 _lastMoveSent;
    private int _debugSpeedTier;
    private bool _debugPenalized;
    private long _ticksAtLastSample;
    private double _sampleTime;
    private int _measuredTicksPerSecond;

    public override void _Ready()
    {
        GameSettings.EnsureApplied();
        GameData data = GameData.Parse(
            FileAccess.GetFileAsString(ItemsPath),
            FileAccess.GetFileAsString(ResourcesPath),
            FileAccess.GetFileAsString(CastellanPath),
            FileAccess.GetFileAsString(VillagersPath),
            FileAccess.GetFileAsString(BuildingsPath),
            FileAccess.GetFileAsString(RecipesPath),
            FileAccess.GetFileAsString(TerrainPath));
        LitanyLibrary litanies = FileAccess.FileExists(GameFiles.Litanies)
            ? LitanyLibrary.Parse(FileAccess.GetFileAsString(GameFiles.Litanies), data)
            : LitanyLibrary.Empty;
        _world = MapLoader.Parse(FileAccess.GetFileAsString(MapPath), data, litanies);

        _view = GetNode<WorldView>("WorldView");
        _view.Build(_world);

        _camera = GetNode<CameraRig>("CameraRig");
        _camera.Target = _view.CastellanNode;
        _camera.SetBounds(new Rect2(0f, 0f, _world.Grid.Width, _world.Grid.Height));
        _camera.RightClicked += OnRightClick;

        _debugLabel = GetNode<Label>("DebugHud/DebugLabel");
        _inventoryLabel = GetNode<Label>("DebugHud/InventoryLabel");

        _hotbar = new Hotbar { Name = "Hotbar" };
        GetNode("DebugHud").AddChild(_hotbar);
        foreach (BuildingType type in data.Buildings)
            if (type.Hotbar)
                _hotbarTypes.Add(type);
        _hotbar.Build(_hotbarTypes, data);
        _hotbar.ShowPage(0);
        _hotbar.SlotClicked += Select;

        // Mana no canto de cima à direita (docs/linha_energia.md: geração × consumo e a carga do Cristal-mãe).
        _manaLabel = new Label
        {
            Name = "ManaLabel",
            HorizontalAlignment = HorizontalAlignment.Right,
            AnchorLeft = 1f, AnchorRight = 1f, OffsetLeft = -720f, OffsetRight = -16f, OffsetTop = 104f, OffsetBottom = 170f,
        };
        _manaLabel.AddThemeColorOverride("font_color", Palette.ManaBlue);
        _manaLabel.AddThemeColorOverride("font_outline_color", Colors.Black);
        _manaLabel.AddThemeConstantOverride("outline_size", 6);
        _manaLabel.AddThemeFontSizeOverride("font_size", 18);
        GetNode("DebugHud").AddChild(_manaLabel);

        _villagerPanel = new VillagerPanel { Name = "VillagerPanel" };
        GetNode("DebugHud").AddChild(_villagerPanel);
        _villagerPanel.Build(_world);

        _inventoryBar = new InventoryBar { Name = "InventoryBar" };
        GetNode("DebugHud").AddChild(_inventoryBar);
        _inventoryBar.Build(data.Items);
        _inventoryBar.ItemClicked += Hold;

        _cinematicOverlay = new CinematicOverlay { Name = "CinematicOverlay" };
        GetNode("DebugHud").AddChild(_cinematicOverlay);

        _perf = new PerfOverlay { Name = "PerfOverlay" };
        GetNode("DebugHud").AddChild(_perf);
        _perf.Setup(_view, GetNode<WorldEnvironment>("WorldEnvironment"), GetNode<DirectionalLight3D>("Sun"),
            GetNode<CanvasItem>("DebugHud/Vignette"));

        _pauseLabel = new Label { Name = "PauseLabel", Text = "Pausado  (Espaço)", HorizontalAlignment = HorizontalAlignment.Right, Visible = false };
        _pauseLabel.SetAnchorsPreset(Control.LayoutPreset.TopRight);
        _pauseLabel.OffsetLeft = -260f;
        _pauseLabel.OffsetRight = -14f;
        _pauseLabel.OffsetTop = 34f; // abaixo da linha de depuração, que ocupa a largura toda
        _pauseLabel.AddThemeFontSizeOverride("font_size", 20);
        _pauseLabel.AddThemeColorOverride("font_color", Palette.Bone);
        _pauseLabel.AddThemeColorOverride("font_outline_color", Colors.Black);
        _pauseLabel.AddThemeConstantOverride("outline_size", 4);
        GetNode("DebugHud").AddChild(_pauseLabel);

        _pauseMenu = new PauseMenu { Name = "PauseMenu" };
        AddChild(_pauseMenu);

        // A linha de status desce para baixo dos botões do inventário.
        _inventoryLabel.OffsetTop = 72f;
        _inventoryLabel.OffsetBottom = 98f;
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is InputEventKey { Pressed: true, Echo: false } key)
            HandleKey(key);

        if (@event is InputEventMouseButton { ButtonIndex: MouseButton.Left } click)
        {
            _leftHeld = click.Pressed;
            _lastBuildCell = null;
            if (click.Pressed && _selected is null && _heldItem is null && _camera.GroundUnder(click.Position) is Vector3 ground
                && _view.VillagerAt(ground) is Villager villager)
            {
                // Shift+clique em outro aldeão copia a ladainha do escolhido para ele (de graça; vários, um a um).
                if (click.ShiftPressed && _villagerPanel.Villager is { Litany: not null } source && source != villager)
                    _world.Enqueue(new CopyLitanyCommand(source.Id, new[] { villager.Id }));
                else
                    _villagerPanel.ShowVillager(villager); // clicar no aldeão mostra a ladainha dele em blocos
                return;
            }
            if (click.Pressed && _world.Teaching is null)
                _villagerPanel.ShowVillager(null); // gravando, o painel fica: clicar é ensinar
            if (click.Pressed && !_clock.Paused && TargetUnder(click.Position) is GridPos cell)
                ActAt(cell);
        }
    }

    private void HandleKey(InputEventKey key)
    {
        Key k = key.PhysicalKeycode;
        if (_perf.HandleKey(k))
            return;
        if (k >= Key.Key1 && k <= Key.Key9)
        {
            int index = _hotbar.Page * Hotbar.PageSize + (int)(k - Key.Key1);
            if (index < _hotbarTypes.Count)
                Select(_selected == _hotbarTypes[index] ? null : index); // mesma tecla desmarca
        }
        else if (k == Key.T && _villagerPanel.Villager is Villager pupil && _world.Teaching is null)
        {
            _world.Enqueue(new StartTeachingCommand(pupil.Id)); // ensinar por demonstração
        }
        else if (k == Key.G && _world.Teaching is not null)
        {
            _world.Enqueue(new MarkGoToCommand()); // "ir até" aqui
        }
        else if (k is Key.Enter or Key.KpEnter && _world.Teaching is not null)
        {
            _world.Enqueue(new FinishTeachingCommand()); // pronto: o aldeão começa a repetir
        }
        else if (k == Key.N && _world.Villagers.Count > 0)
        {
            // Próximo aldeão (na ordem em que nasceram): mostra a ladainha dele em blocos sem precisar mirar.
            int next = _villagerPanel.Villager is Villager current ? (IndexOf(current) + 1) % _world.Villagers.Count : 0;
            _villagerPanel.ShowVillager(_world.Villagers[next]);
        }
        else if (k == Key.Tab)
        {
            _hotbar.ShowPage(_hotbar.Page + 1); // próxima página da barra de construção
        }
        else if (k == Key.R && _selected is not null)
        {
            _buildDirection = _buildDirection.RotatedClockwise();
        }
        else if (k == Key.Space)
        {
            SetPaused(!_clock.Paused);
        }
        else if (k == Key.E && !_clock.Paused)
        {
            _world.Enqueue(new OperatePostCommand()); // assume o posto da máquina encostada, ou sai dele
        }
        else if (k == Key.P && !_clock.Paused)
        {
            _world.Enqueue(new HandCraftCommand("purify")); // mais uma purificação à mão na fila
        }
        else if (k == Key.M && !_clock.Paused)
        {
            _world.Enqueue(new HandCraftCommand("mold")); // mais uma casca moldada à mão na fila
        }
        else if (k == Key.H)
        {
            _view.ShowCollision = !_view.ShowCollision; // formas de colisão no chão
        }
        else if (k == Key.O)
        {
            Outline.Enabled = !Outline.Enabled; // prova do contorno fino escuro: liga e desliga tudo
        }
        else if (k == Key.C)
        {
            ToggleCinematic();
        }
        else if (k == Key.V)
        {
            // Depuração: alterna o patamar de velocidade de todos (até existir pesquisa ou era).
            _debugSpeedTier = (_debugSpeedTier + 1) % _world.Data.Villagers.SpeedTiers.Count;
            _world.Enqueue(new SetSpeedTierCommand(_debugSpeedTier));
        }
        else if (key.Keycode is Key.Bracketleft or Key.Bracketright)
        {
            // Depuração temporária: [ e ] baixam e sobem a velocidade dela em 0,1 cél/s (tecla lógica: no teclado
            // ABNT o [ fica em outra posição física). O valor escolhido pelo Arthur vira o speed de data/castellan.json.
            float step = key.Keycode == Key.Bracketright ? 0.1f : -0.1f;
            float speed = Mathf.Round((_world.Castellan.Stats.CellsPerSecond + step) * 10f) / 10f;
            _world.Enqueue(new SetCastellanSpeedCommand(speed));
        }
        else if (k == Key.B)
        {
            // Depuração: penalidade de fome ou moral baixa em todos (até existirem fome e moral).
            _debugPenalized = !_debugPenalized;
            _world.Enqueue(new SetPenalizedCommand(_debugPenalized));
        }
        else if (k == Key.Escape)
        {
            if (_camera.IsCinematic)
            {
                ToggleCinematic();
                return;
            }
            if (_world.Teaching is not null)
            {
                _world.Enqueue(new CancelTeachingCommand()); // Esc cancela a gravação
                return;
            }
            if (_villagerPanel.Villager is not null)
            {
                _villagerPanel.ShowVillager(null); // Esc fecha o painel do aldeão antes de abrir o menu
                return;
            }
            if (_selected is null && _heldItem is null)
            {
                OpenPauseMenu();
                return;
            }
            Select(null);
            Hold(null);
        }
    }

    /// <summary>Abre o menu de pausa. O Esc que abriu não pode chegar ao menu, senão ele fecharia na hora.</summary>
    private void OpenPauseMenu()
    {
        GetViewport().SetInputAsHandled();
        _leftHeld = false; // o soltar do botão não chega com a árvore pausada
        _pauseMenu.Open();
    }

    /// <summary>
    /// Pausa ou continua o tempo do jogo. Na pausa a cena do mundo para de processar (animações, efeitos e
    /// partículas congelam onde estão) e a câmera continua livre.
    /// </summary>
    private void SetPaused(bool paused)
    {
        _clock.Paused = paused;
        _view.ProcessMode = paused ? ProcessModeEnum.Disabled : ProcessModeEnum.Inherit;
    }

    /// <summary>
    /// Entra na câmera cinematográfica no que está sob o cursor (Castelão, aldeão, construção, recurso;
    /// sem nada, o Castelão) ou sai dela. Solta o que estava escolhido para não construir sem querer.
    /// A árvore sob o cursor é achada pelo mesmo teste do clique (copa e tronco); um personagem mais perto da câmera
    /// que ela ainda vence.
    /// </summary>
    private void ToggleCinematic()
    {
        if (_camera.IsCinematic)
        {
            _camera.ExitCinematic();
            return;
        }
        Select(null);
        Hold(null);
        _focus = CinematicTarget() ?? _view.CastellanFocus();
        _camera.EnterCinematic(_focus.Node, _focus.Height, _focus.Distance);
    }

    private FocusTarget? CinematicTarget()
    {
        if (CursorOverWorld() is not Vector2 cursor)
            return null;
        Vector3? ground = _camera.GroundUnder(cursor);
        FocusTarget? byGround = ground is Vector3 g ? _view.FindFocus(g) : null;
        (Vector3 origin, Vector3 direction) = _camera.RayAt(cursor);
        float toGround = ground is Vector3 gp ? origin.DistanceTo(gp) : float.MaxValue;
        if (_view.PickResource(origin, direction, toGround, out float toResource) is not ResourceNode resource)
            return byGround;
        if (byGround is not null && _view.IsCharacter(byGround) && origin.DistanceTo(byGround.Node.GlobalPosition) < toResource)
            return byGround;
        return _view.ResourceFocus(resource) ?? byGround;
    }

    /// <summary>
    /// Clique esquerdo numa célula: constrói, põe o item da mão, recolhe de um baú ou coleta.
    /// A simulação confere tudo (alcance, itens, espaço).
    /// </summary>
    private void ActAt(GridPos cell)
    {
        _lastBuildCell = cell;
        if (_selected is not null)
            _world.Enqueue(new BuildCommand(_selected.Kind, cell, _buildDirection));
        else if (_heldItem is not null)
            _world.Enqueue(new InsertItemCommand(cell, _heldItem));
        else if (_world.BuildingAt(cell) is { } b && (b.Storage is not null || b.Machine is not null || b.Workplace is not null))
            _world.Enqueue(new TakeAllCommand(cell));
        else
            _world.Enqueue(new GatherCommand(cell));
    }

    private void OnRightClick(Vector2 screenPos)
    {
        if (_selected is not null || _heldItem is not null)
        {
            Select(null);
            Hold(null);
        }
        else if (!_clock.Paused && CellUnder(screenPos) is GridPos cell)
        {
            _world.Enqueue(new DeconstructCommand(cell));
        }
    }

    /// <summary>Escolhe uma construção da barra (ou nenhuma). Solta o item da mão.</summary>
    private void Select(int? index)
    {
        _selected = index is int i ? _hotbarTypes[i] : null;
        _hotbar.ShowSelected(index);
        if (_selected is not null)
            Hold(null);
    }

    /// <summary>Segura um item do inventário na mão (ou nenhum). Desmarca a construção.</summary>
    private void Hold(string? kind)
    {
        _heldItem = kind;
        _inventoryBar.ShowHeld(kind);
        if (kind is not null)
        {
            _selected = null;
            _hotbar.ShowSelected(null);
        }
    }

    public override void _Process(double delta)
    {
        long started = System.Diagnostics.Stopwatch.GetTimestamp();
        if (!_clock.Paused)
            SendMoveInput();

        Vector2? cursor = CursorOverWorld();
        GridPos? hovered = cursor is Vector2 c ? TargetUnder(c) : null;

        // Segurar o esquerdo e arrastar repete a ação célula a célula (fileira de esteiras, itens em várias).
        if (_leftHeld && !_clock.Paused && (_selected is not null || _heldItem is not null) && hovered is GridPos cell && cell != _lastBuildCell)
            ActAt(cell);

        int ticks = _clock.Advance(delta);
        for (int i = 0; i < ticks; i++)
            _world.Tick();

        if (!_clock.Paused)
            _view.Render(_clock.Alpha, delta);
        _perf.GameCpuMs = System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds;

        // Na cinematográfica, a interface some e só ficam as faixas com a legenda ao vivo.
        bool cinematic = _camera.IsCinematic;
        if (cinematic && _focus is not null)
            _cinematicOverlay.SetCaption(_focus.Describe() + "     (C ou Esc sai)");
        _cinematicOverlay.Show(cinematic);
        _hotbar.Visible = !cinematic;
        _inventoryBar.Visible = !cinematic;
        _inventoryLabel.Visible = !cinematic;
        if (cinematic)
            _villagerPanel.Visible = false;
        else if (_villagerPanel.Villager is not null)
            _villagerPanel.Visible = true;
        _debugLabel.Visible = !cinematic;
        _view.InfoMode = Input.IsKeyPressed(Key.Alt);
        _view.IconsVisible = !cinematic;
        _pauseLabel.Visible = _clock.Paused && !cinematic;
        if (cinematic)
            hovered = null;

        _view.ShowHover(_selected is null ? hovered : null);
        _view.ShowGhost(_selected, hovered, _buildDirection);
        _view.ShowBuildingInfo(hovered);
        _hotbar.ShowAffordable(_world.Castellan.Inventory);
        _inventoryBar.ShowCounts(_world.Castellan.Inventory);
        UpdateHud(delta);
    }

    /// <summary>Cursor sobre o mundo; null se saiu da janela ou está em cima da barra.</summary>
    private Vector2? CursorOverWorld() =>
        GetViewport().GuiGetHoveredControl() is null ? _camera.Cursor : null;

    /// <summary>
    /// WASD é relativo à câmera; a simulação quer direção no mundo.
    /// Só manda comando quando a direção muda, para não encher a fila.
    /// </summary>
    private void SendMoveInput()
    {
        Vector2 input = Input.GetVector("move_left", "move_right", "move_forward", "move_back");
        Vector3 world = new Vector3(input.X, 0f, input.Y).Rotated(Vector3.Up, _camera.Yaw);
        var direction = new System.Numerics.Vector2(world.X, world.Z);

        // Andar traz a câmera solta de volta para o Castelão.
        if (direction != System.Numerics.Vector2.Zero)
            _camera.ReturnToTarget();

        if (direction == _lastMoveSent)
            return;
        _world.Enqueue(new MoveCommand(direction));
        _lastMoveSent = direction;
    }

    /// <summary>
    /// Célula apontada: sem construção nem item na mão, um recurso sob o cursor (a copa inteira da árvore conta) aponta
    /// para a célula dele; senão, a célula do chão sob o cursor (construir e pôr item continuam pelo chão).
    /// </summary>
    private GridPos? TargetUnder(Vector2 screenPos)
    {
        GridPos? ground = CellUnder(screenPos);
        if (_selected is not null || _heldItem is not null)
            return ground;
        (Vector3 origin, Vector3 direction) = _camera.RayAt(screenPos);
        float toGround = _camera.GroundUnder(screenPos) is Vector3 g ? origin.DistanceTo(g) : float.MaxValue;
        return _view.PickResource(origin, direction, toGround)?.Cell ?? ground;
    }

    /// <summary>Célula do chão sob uma posição da tela. A célula x ocupa [x, x+1] no mundo.</summary>
    private GridPos? CellUnder(Vector2 screenPos) =>
        _camera.GroundUnder(screenPos) is Vector3 p
            ? new GridPos(Mathf.FloorToInt(p.X), Mathf.FloorToInt(p.Z))
            : null;

    private void UpdateHud(double delta)
    {
        _sampleTime += delta;
        if (_sampleTime >= 1.0)
        {
            _measuredTicksPerSecond = (int)(_world.TickCount - _ticksAtLastSample);
            _ticksAtLastSample = _world.TickCount;
            _sampleTime -= 1.0;
        }
        Castellan castellan = _world.Castellan;
        System.Numerics.Vector2 p = castellan.Position;
        _debugLabel.Text =
            $"Tick {_world.TickCount}  |  {_measuredTicksPerSecond} ticks/s (alvo {(_clock.Paused ? 0 : SimClock.TicksPerSecond)})  |  " +
            $"{Engine.GetFramesPerSecond()} FPS  |  Castelão ({p.X:0.0}, {p.Y:0.0}) a {castellan.Stats.CellsPerSecond:0.0} cél/s [ ]  |  grama: {_view.GrassTufts} tufos  |  " +
            $"aldeões: patamar {_debugSpeedTier + 1}/{_world.Data.Villagers.SpeedTiers.Count} ({_world.Data.Villagers.SpeedTiers[_debugSpeedTier]:0.00} cél/s){(_debugPenalized ? ", com penalidade" : "")}  [V patamar, B penalidade]  [O contorno {(Outline.Enabled ? "ligado" : "desligado")}]  [H colisão]";

        _manaLabel.Text = ManaText();

        _inventoryLabel.Text = _selected is not null
            ? $"Construindo {_selected.Name} ({DirectionName(_buildDirection)}) — R gira, botão direito cancela"
            : _heldItem is not null
                ? $"Segurando {_world.Data.Item(_heldItem).Name} — clique numa esteira, baú ou máquina; botão direito solta"
                : string.Join("   ", HandLines(castellan));
    }

    private int IndexOf(Villager villager)
    {
        for (int i = 0; i < _world.Villagers.Count; i++)
            if (_world.Villagers[i] == villager)
                return i;
        return -1;
    }

    /// <summary>Geração × consumo de cada rede de mana (a soma, se houver mais de uma) e a carga do Cristal-mãe.</summary>
    private string ManaText()
    {
        var lines = new List<string>();
        IReadOnlyList<ManaNetwork> networks = _world.ManaNetworks;
        if (networks.Count == 0)
            lines.Add("Mana: nenhuma torre");
        for (int i = 0; i < networks.Count; i++)
        {
            ManaNetwork n = networks[i];
            string name = networks.Count > 1 ? $"Rede {i + 1}" : "Mana";
            string state = n.Supply <= 0f ? "sem geração" : n.Satisfaction < 1f ? $"FALTA ({n.Satisfaction:P0})" : $"sobra {n.Surplus:0.0}/s";
            lines.Add($"{name}: gera {n.Supply:0.0}/s · consome {Mathf.Min(n.Demand, n.Supply):0.0}/s · {state}");
        }
        foreach (Building b in _world.Buildings)
            if (b.Type.SpawnsVillager && b.Machine is MachineState m)
                lines.Add($"{b.Type.Name}: " + (m.IsWorking ? $"formando {m.Progress:P0}" : "parado") + $" · {b.VillagersFormed} formados" +
                    (b.LastFormedTick >= 0 ? $" (último há {(_world.TickCount - b.LastFormedTick) / SimClock.TicksPerSecond} s)" : ""));
        return string.Join("\n", lines);
    }

    /// <summary>O que ela faz à mão agora: coleta, posto, purificação (com a fila) e as teclas.</summary>
    private static IEnumerable<string> HandLines(Castellan castellan)
    {
        if (castellan.GatherTarget is ResourceNode node)
            yield return $"Coletando {node.Type.Name} {castellan.GatherProgress:P0} (restam {node.Remaining})";
        if (castellan.DigCell is not null)
            yield return $"Cavando argila {castellan.WorkProgress:P0}";
        if (castellan.Post is Building post)
            yield return $"No posto: {post.Type.Name} (E ou andar sai)";
        if (castellan.HandBusy || castellan.HandQueue > 0)
        {
            string what = castellan.HandCurrent?.Recipe.Id == "mold" ? "Moldando casca" : castellan.HandCurrent is null ? "À mão" : "Purificando à mão";
            yield return (castellan.HandNeedsWater ? "Moldar: chegue perto da água" : $"{what} {castellan.HandProgress:P0}")
                + (castellan.HandQueue > 0 ? $" (+{castellan.HandQueue} na fila)" : "");
        }
        if (castellan.GatherTarget is null && castellan.DigCell is null && castellan.Post is null && !castellan.HandBusy)
            yield return "E opera a máquina encostada  ·  P purifica (2 podres → 1 puro)  ·  M molda casca perto da água (2 argilas)  ·  clique no aldeão ou N: a ladainha dele";
    }

    private static string DirectionName(Direction d) => d switch
    {
        Direction.North => "norte",
        Direction.East => "leste",
        Direction.South => "sul",
        _ => "oeste",
    };
}
