using System;
using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Ícones de estado dos aldeões (data/villager_status.json): por padrão só em quem tem problema; no modo de informação
/// (Alt), em todos. Um MultiMesh só para todos os ícones (uma chamada de desenho), preenchido a cada quadro por um
/// buffer; as formas são desenhadas por código num atlas (uma célula por estado: selo vermelho de aviso nos problemas,
/// roxo nos outros, moldura e desenho em osso).
/// </summary>
public partial class VillagerIcons : MultiMeshInstance3D
{
    private const int CellPx = 64;
    private const int FloatsPerInstance = 16; // transformação 3×4 + dados por instância

    private VillagerStatusTable _table = null!;
    private float _height;
    private float[] _buffer = Array.Empty<float>();

    public void Build(VillagerStatusTable table, int capacity, Rect2 bounds)
    {
        _table = table;
        VisualSettings.IconSettings icon = VisualSettings.Current.VillagerIcon;
        _height = icon.Height;
        var material = new ShaderMaterial { Shader = GD.Load<Shader>("res://src/View/VillagerIcon.gdshader") };
        material.SetShaderParameter("atlas", BuildAtlas(table));
        material.SetShaderParameter("cells", (float)VillagerStatuses.All.Length);
        material.SetShaderParameter("world_size", icon.WorldSize);
        material.SetShaderParameter("min_px", icon.MinPx);
        material.SetShaderParameter("max_px", icon.MaxPx);
        material.SetShaderParameter("reference_height", icon.ReferenceHeight);
        Multimesh = new MultiMesh
        {
            TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
            UseCustomData = true,
            InstanceCount = Math.Max(capacity, 1),
            VisibleInstanceCount = 0,
            Mesh = new QuadMesh { Size = Vector2.One, Material = material },
            // Os aldeões andam: a caixa cobre o mapa inteiro para o MultiMesh nunca ser recortado pela câmera.
            CustomAabb = new Aabb(new Vector3(bounds.Position.X, 0f, bounds.Position.Y), new Vector3(bounds.Size.X, 4f, bounds.Size.Y)),
        };
        CastShadow = ShadowCastingSetting.Off;
        _buffer = new float[Multimesh.InstanceCount * FloatsPerInstance];
    }

    /// <summary>Um ícone por aldeão que deve mostrar (com problema, ou todos com <paramref name="showAll"/>).</summary>
    public void UpdateFrom(IEnumerable<(Villager Villager, Vector3 Position)> villagers, bool showAll)
    {
        int n = 0;
        int capacity = Multimesh.InstanceCount;
        foreach ((Villager villager, Vector3 position) in villagers)
        {
            VillagerStatus status = villager.Status;
            if (n >= capacity || (!showAll && !_table[status].Problem))
                continue;
            int o = n * FloatsPerInstance;
            _buffer[o + 0] = 1f; _buffer[o + 1] = 0f; _buffer[o + 2] = 0f; _buffer[o + 3] = position.X;
            _buffer[o + 4] = 0f; _buffer[o + 5] = 1f; _buffer[o + 6] = 0f; _buffer[o + 7] = position.Y + _height;
            _buffer[o + 8] = 0f; _buffer[o + 9] = 0f; _buffer[o + 10] = 1f; _buffer[o + 11] = position.Z;
            _buffer[o + 12] = (int)status; _buffer[o + 13] = 0f; _buffer[o + 14] = 0f; _buffer[o + 15] = 0f;
            n++;
        }
        Multimesh.Buffer = _buffer;
        Multimesh.VisibleInstanceCount = n;
    }

    private static ImageTexture BuildAtlas(VillagerStatusTable table)
    {
        VillagerStatus[] all = VillagerStatuses.All;
        var image = Image.CreateEmpty(CellPx * all.Length, CellPx, false, Image.Format.Rgba8);
        for (int i = 0; i < all.Length; i++)
        {
            VillagerStatusTable.Entry entry = table[all[i]];
            Color badge = entry.Problem ? Palette.Warning : Palette.DeepPurple.Lightened(0.2f);
            DrawCell(image, i * CellPx, badge, entry.Icon);
        }
        image.GenerateMipmaps();
        return ImageTexture.CreateFromImage(image);
    }

    /// <summary>Selo redondo (fundo, moldura em osso) com o desenho do estado em osso, por distância com borda suave.</summary>
    private static void DrawCell(Image image, int x0, Color badge, string icon)
    {
        float aa = 2f / CellPx * 1.2f;
        for (int py = 0; py < CellPx; py++)
        for (int px = 0; px < CellPx; px++)
        {
            // -1..1, com y para cima.
            float x = (px + 0.5f) / CellPx * 2f - 1f;
            float y = 1f - (py + 0.5f) / CellPx * 2f;
            float r = MathF.Sqrt(x * x + y * y);
            float outer = Cover(r - 0.94f, aa);
            float fill = Cover(r - 0.78f, aa);
            float glyph = Cover(Glyph(icon, x, y), aa) * fill;
            Color c = Palette.Bone.Lerp(badge, fill);
            c = c.Lerp(Palette.Bone, glyph);
            c.A = outer;
            image.SetPixel(x0 + px, py, c);
        }
    }

    private static float Cover(float sd, float aa) => Math.Clamp(0.5f - sd / aa, 0f, 1f);

    private static float Glyph(string icon, float x, float y) => icon switch
    {
        "dots" => Min(Circle(x + 0.38f, y, 0.12f), Circle(x, y, 0.12f), Circle(x - 0.38f, y, 0.12f)),
        "house" => MathF.Min(Box(x, y + 0.2f, 0.3f, 0.25f), Triangle(x, y - 0.05f, 0.42f, 0.4f)),
        "cross" => MathF.Min(Segment(x, y, -0.36f, -0.36f, 0.36f, 0.36f, 0.11f), Segment(x, y, -0.36f, 0.36f, 0.36f, -0.36f, 0.11f)),
        "empty" => MathF.Min(MathF.Abs(Circle(x, y, 0.32f)) - 0.07f, Segment(x, y, -0.42f, -0.42f, 0.42f, 0.42f, 0.07f)),
        "moon" => MathF.Max(Circle(x, y, 0.42f), -Circle(x - 0.22f, y - 0.14f, 0.36f)),
        "diamond" => (MathF.Abs(x) + MathF.Abs(y) - 0.44f) * 0.7071f,
        "box" => MathF.Min(Box(x, y + 0.08f, 0.34f, 0.24f), Segment(x, y, -0.18f, 0.24f, 0.18f, 0.24f, 0.06f)),
        "arrow" => MathF.Min(Segment(x, y, -0.18f, 0.38f, 0.22f, 0f, 0.11f), Segment(x, y, 0.22f, 0f, -0.18f, -0.38f, 0.11f)),
        "pause" => MathF.Min(Box(x - 0.17f, y, 0.08f, 0.32f), Box(x + 0.17f, y, 0.08f, 0.32f)),
        _ => Circle(x, y, 0.2f),
    };

    private static float Min(float a, float b, float c) => MathF.Min(a, MathF.Min(b, c));

    private static float Circle(float x, float y, float r) => MathF.Sqrt(x * x + y * y) - r;

    private static float Box(float x, float y, float hx, float hy)
    {
        float dx = MathF.Abs(x) - hx, dy = MathF.Abs(y) - hy;
        float ox = MathF.Max(dx, 0f), oy = MathF.Max(dy, 0f);
        return MathF.Sqrt(ox * ox + oy * oy) + MathF.Min(MathF.Max(dx, dy), 0f);
    }

    private static float Segment(float x, float y, float ax, float ay, float bx, float by, float r)
    {
        float pax = x - ax, pay = y - ay, bax = bx - ax, bay = by - ay;
        float h = Math.Clamp((pax * bax + pay * bay) / (bax * bax + bay * bay), 0f, 1f);
        float dx = pax - bax * h, dy = pay - bay * h;
        return MathF.Sqrt(dx * dx + dy * dy) - r;
    }

    /// <summary>Triângulo de base 2·hw em y = 0 e ponta em y = h (telhado).</summary>
    private static float Triangle(float x, float y, float hw, float h)
    {
        // Interseção de três semiplanos (aproximação de distância, suficiente para a borda suave).
        float slope = MathF.Sqrt(h * h + hw * hw);
        float side = (MathF.Abs(x) * h + y * hw - h * hw) / slope;
        return MathF.Max(side, -y);
    }
}
