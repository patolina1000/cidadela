using Godot;

namespace Cidadela.View;

/// <summary>
/// Câmera top-down (GDD, seções 12 e 20), tudo no mouse:
/// - Seguindo: presa no Castelão. Com o cursor perto da borda, espia um pouco naquela direção
///   (estilo Nuclear Throne / Enter the Gungeon); no meio da tela, não se mexe.
/// - Solta: segurar o botão do meio arrasta o mundo (o ponto agarrado fica sob o cursor)
///   e a câmera para exatamente onde foi solta. Volta a seguir quando o Castelão anda.
/// - Girar: segurar o botão direito e arrastar para os lados gira livre; ao soltar, encaixa
///   no múltiplo de 90° mais próximo (a leitura das esteiras nunca fica torta). Um clique
///   direito sem arrastar fica livre para outras ações.
/// - Zoom na roda, com inclinação fixa (estilo Factorio).
/// O nó fica no chão, no ponto que a câmera olha; a câmera filha fica a uma distância e inclinação.
/// </summary>
public partial class CameraRig : Node3D
{
    /// <summary>Distância no zoom padrão (zoom 1).</summary>
    [Export] public float DefaultDistance = 16f;

    /// <summary>Zoom mínimo (mais afastado). Factorio: cerca de 0,4.</summary>
    [Export] public float MinZoom = 0.4f;

    /// <summary>Zoom máximo (mais perto).</summary>
    [Export] public float MaxZoom = 2.5f;

    /// <summary>Quanto cada clique da roda multiplica o zoom. Factorio: cerca de 1,1.</summary>
    [Export] public float ZoomStep = 1.1f;

    /// <summary>Inclinação fixa em graus acima do horizonte.</summary>
    [Export] public float Pitch = 55f;

    /// <summary>Quão rápido o zoom alcança o alvo (maior = mais rápido).</summary>
    [Export] public float ZoomSmoothing = 15f;

    /// <summary>Quanto a câmera espia com o cursor na borda da tela, em células, no zoom 1.</summary>
    [Export] public float LookAheadCells = 2.5f;

    /// <summary>
    /// Fração central da tela (0..1, de cada lado a partir do centro) em que o cursor não move a câmera.
    /// 0,6 = só os 40% mais perto de cada borda fazem espiar.
    /// </summary>
    [Export] public float LookAheadDeadZone = 0.6f;

    /// <summary>Quão rápido o espiar (e a volta ao Castelão) alcança o alvo.</summary>
    [Export] public float LookAheadSmoothing = 4f;

    /// <summary>Graus de giro por pixel arrastado com o botão direito.</summary>
    [Export] public float RotateDegreesPerPixel = 0.3f;

    /// <summary>Pixels que o botão direito precisa andar antes de virar giro (abaixo disso é clique).</summary>
    [Export] public float RotateDragThreshold = 8f;

    /// <summary>Quão rápido o giro encaixa no múltiplo de 90° depois de soltar.</summary>
    [Export] public float RotateSnapSmoothing = 12f;

    /// <summary>O que a câmera segue.</summary>
    public Node3D? Target { get; set; }

    /// <summary>Giro atual em radianos, para converter o WASD em direção no mundo.</summary>
    public float Yaw => _yaw;

    /// <summary>Último cursor dentro do jogo, ou null se o mouse saiu da janela.</summary>
    public Vector2? Cursor => _cursor;

    private Camera3D _camera = null!;
    private float _yaw;
    private float _targetYaw;
    private bool _rotatePressed;
    private bool _rotating;
    private float _rotatePressX;
    private float _zoom = 1f;
    private float _targetZoom = 1f;

    // Seguindo: foco = alvo + deslocamento suavizado.
    private Vector3 _offset;

    // Último cursor visto dentro do jogo; sem cursor (saiu da janela ou perdeu o foco), não espia.
    private Vector2? _cursor;

    // Solta: foco livre, controlado pelo arrasto.
    private bool _free;
    private bool _dragging;
    private Vector3 _grabPoint;
    private Rect2 _bounds = new(new Vector2(-1e6f, -1e6f), new Vector2(2e6f, 2e6f));

    public override void _Ready()
    {
        _camera = new Camera3D { Name = "Camera", Fov = 45f, Current = true };
        AddChild(_camera);
        ApplyTransform();
    }

    /// <summary>Limita o foco da câmera solta a uma área do mapa (em X/Z).</summary>
    public void SetBounds(Rect2 bounds) => _bounds = bounds;

    /// <summary>Volta a seguir o Castelão, suavemente, a partir de onde a câmera está.</summary>
    public void ReturnToTarget()
    {
        if (!_free || _dragging || Target is null)
            return;
        _free = false;
        _offset = Position - GroundPoint(Target);
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is InputEventMouseButton mouse)
        {
            if (mouse.ButtonIndex == MouseButton.Middle)
            {
                if (mouse.Pressed && GroundUnder(mouse.Position) is Vector3 grab)
                {
                    _dragging = true;
                    _free = true;
                    _grabPoint = grab;
                }
                else
                {
                    _dragging = false;
                }
            }
            else if (mouse.ButtonIndex == MouseButton.Right)
            {
                _rotatePressed = mouse.Pressed;
                _rotatePressX = mouse.Position.X;
                if (!mouse.Pressed && _rotating)
                {
                    _rotating = false;
                    _targetYaw = SnapToQuarter(_yaw);
                }
            }
            else if (mouse.Pressed && mouse.ButtonIndex == MouseButton.WheelUp)
            {
                _targetZoom = Mathf.Min(_targetZoom * ZoomStep, MaxZoom);
            }
            else if (mouse.Pressed && mouse.ButtonIndex == MouseButton.WheelDown)
            {
                _targetZoom = Mathf.Max(_targetZoom / ZoomStep, MinZoom);
            }
        }
        else if (@event is InputEventMouseMotion motion)
        {
            _cursor = motion.Position;
            if (_dragging)
                DragTo(motion.Position);
            if (_rotatePressed)
                RotateTo(motion.Position.X);
        }
    }

    public override void _Notification(int what)
    {
        if (what == NotificationWMMouseExit || what == NotificationApplicationFocusOut)
            _cursor = null;
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        _zoom = Mathf.Lerp(_zoom, _targetZoom, 1f - Mathf.Exp(-ZoomSmoothing * dt));
        if (!_rotating)
            _yaw = Mathf.Lerp(_yaw, _targetYaw, 1f - Mathf.Exp(-RotateSnapSmoothing * dt));

        if (!_free && Target is not null)
        {
            // O Castelão fica travado; só o deslocamento de espiar é suavizado.
            float blend = 1f - Mathf.Exp(-LookAheadSmoothing * dt);
            _offset = _offset.Lerp(LookAheadOffset(), blend);
            Position = GroundPoint(Target) + _offset;
        }

        ApplyTransform();
    }

    /// <summary>
    /// Cursor dentro da zona morta = 0; da zona morta até a borda cresce com curva suave até
    /// <see cref="LookAheadCells"/> (maior quanto mais afastado o zoom).
    /// Usa a posição do cursor na tela, não no chão, para a câmera não correr atrás de si mesma.
    /// </summary>
    private Vector3 LookAheadOffset()
    {
        Rect2 view = GetViewport().GetVisibleRect();
        if (_cursor is not Vector2 cursor || view.Size.X <= 0f || view.Size.Y <= 0f)
            return Vector3.Zero;

        Vector2 half = view.Size / 2f;
        Vector2 fromCenter = (cursor - half) / half;
        fromCenter = new Vector2(EdgeAmount(fromCenter.X), EdgeAmount(fromCenter.Y));
        // Direita e baixo da tela, girados pelo giro da câmera.
        return new Vector3(fromCenter.X, 0f, fromCenter.Y).Rotated(Vector3.Up, _yaw) * (LookAheadCells / _zoom);
    }

    /// <summary>-1..1 do centro à borda → 0 na zona morta, depois sobe suave (smoothstep) até ±1.</summary>
    private float EdgeAmount(float v)
    {
        float t = Mathf.Clamp((Mathf.Abs(v) - LookAheadDeadZone) / (1f - LookAheadDeadZone), 0f, 1f);
        return Mathf.Sign(v) * t * t * (3f - 2f * t);
    }

    /// <summary>Gira livre seguindo o mouse, depois que o arrasto passa do limite de clique.</summary>
    private void RotateTo(float mouseX)
    {
        float dx = mouseX - _rotatePressX;
        if (!_rotating)
        {
            if (Mathf.Abs(dx) < RotateDragThreshold)
                return;
            _rotating = true;
            _rotatePressX = mouseX;
            return;
        }

        // Como agarrar o mundo: arrastar para a direita gira o mundo para a direita.
        _yaw -= Mathf.DegToRad(dx * RotateDegreesPerPixel);
        _targetYaw = _yaw;
        _rotatePressX = mouseX;
    }

    private static float SnapToQuarter(float yaw) => Mathf.Round(yaw / (Mathf.Pi / 2f)) * (Mathf.Pi / 2f);

    /// <summary>Move o foco para que o ponto agarrado volte a ficar sob o cursor.</summary>
    private void DragTo(Vector2 screenPos)
    {
        if (GroundUnder(screenPos) is not Vector3 current)
            return;

        Position = ClampToBounds(Position + (_grabPoint - current));
        ApplyTransform();
    }

    /// <summary>Ponto do chão (y = 0) sob uma posição da tela, ou null se o raio não chega ao chão.</summary>
    public Vector3? GroundUnder(Vector2 screenPos)
    {
        Vector3 origin = _camera.ProjectRayOrigin(screenPos);
        Vector3 dir = _camera.ProjectRayNormal(screenPos);
        if (dir.Y >= -0.0001f)
            return null;
        float t = -origin.Y / dir.Y;
        return origin + dir * t;
    }

    private Vector3 ClampToBounds(Vector3 p) => new(
        Mathf.Clamp(p.X, _bounds.Position.X, _bounds.End.X),
        0f,
        Mathf.Clamp(p.Z, _bounds.Position.Y, _bounds.End.Y));

    private static Vector3 GroundPoint(Node3D target) =>
        new(target.GlobalPosition.X, 0f, target.GlobalPosition.Z);

    private void ApplyTransform()
    {
        Rotation = new Vector3(0f, _yaw, 0f);
        float distance = DefaultDistance / _zoom;
        float pitch = Mathf.DegToRad(Pitch);
        _camera.Position = new Vector3(0f, Mathf.Sin(pitch) * distance, Mathf.Cos(pitch) * distance);
        _camera.Rotation = new Vector3(-pitch, 0f, 0f);
    }
}
