using System;
using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Tecla H do jogo: desenha no chão as formas de colisão da simulação, para ver onde cada coisa bate. Amarelo: o que os
/// recursos bloqueiam (polígono da base da pedra e do veio, círculo do tronco); vermelho: células cheias (construções
/// sólidas); branco: o corpo da protagonista; azul: o corpo de cada aldeão. Linhas por cima de tudo, refeitas a cada quadro
/// só enquanto a tecla está ligada.
/// </summary>
public partial class CollisionDebug : MeshInstance3D
{
    private const float Height = 0.04f;
    private const int CircleSegments = 24;

    private static readonly Color ResourceColor = new(1f, 0.85f, 0.2f);
    private static readonly Color SolidColor = new(1f, 0.3f, 0.25f);
    private static readonly Color CastellanColor = new(1f, 1f, 1f);
    private static readonly Color VillagerColor = new(0.45f, 0.75f, 1f);

    private readonly ImmediateMesh _mesh = new();

    public override void _Ready()
    {
        Mesh = _mesh;
        CastShadow = ShadowCastingSetting.Off;
        MaterialOverride = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            VertexColorUseAsAlbedo = true,
            NoDepthTest = true,
            RenderPriority = 10,
        };
        Visible = false;
    }

    public void Draw(SimWorld world)
    {
        _mesh.ClearSurfaces();
        _mesh.SurfaceBegin(Mesh.PrimitiveType.Lines);
        foreach (ResourceNode resource in world.Resources)
        {
            if (resource.IsDepleted)
                continue;
            if (resource.Shape is ResourceShape shape)
            {
                foreach ((System.Numerics.Vector2 c, float r) in shape.Circles)
                    Circle(c, r, ResourceColor);
                for (int i = 0; i < shape.Polygon.Count; i++)
                    Line(shape.Polygon[i], shape.Polygon[(i + 1) % shape.Polygon.Count], ResourceColor);
            }
            else
            {
                Square(resource.Cell, SolidColor);
            }
        }
        foreach (Building building in world.Buildings)
            if (building.Type.Solid)
                Square(building.Cell, SolidColor);
        Circle(world.Castellan.Position, world.Castellan.Stats.Radius, CastellanColor);
        foreach (Villager villager in world.Villagers)
            Circle(villager.Position, villager.Stats.Radius, VillagerColor);
        _mesh.SurfaceEnd();
    }

    // Posições da simulação: (x, z) é o centro da célula x, z; no mundo, o centro fica em x + 0,5.
    private void Vertex(System.Numerics.Vector2 p, Color color)
    {
        _mesh.SurfaceSetColor(color);
        _mesh.SurfaceAddVertex(new Vector3(p.X + 0.5f, Height, p.Y + 0.5f));
    }

    private void Line(System.Numerics.Vector2 a, System.Numerics.Vector2 b, Color color)
    {
        Vertex(a, color);
        Vertex(b, color);
    }

    private void Circle(System.Numerics.Vector2 center, float radius, Color color)
    {
        for (int i = 0; i < CircleSegments; i++)
        {
            float a0 = i * MathF.Tau / CircleSegments, a1 = (i + 1) * MathF.Tau / CircleSegments;
            Line(center + new System.Numerics.Vector2(MathF.Cos(a0), MathF.Sin(a0)) * radius,
                center + new System.Numerics.Vector2(MathF.Cos(a1), MathF.Sin(a1)) * radius, color);
        }
    }

    private void Square(GridPos cell, Color color)
    {
        var a = new System.Numerics.Vector2(cell.X - 0.5f, cell.Z - 0.5f);
        var b = new System.Numerics.Vector2(cell.X + 0.5f, cell.Z - 0.5f);
        var c = new System.Numerics.Vector2(cell.X + 0.5f, cell.Z + 0.5f);
        var d = new System.Numerics.Vector2(cell.X - 0.5f, cell.Z + 0.5f);
        Line(a, b, color); Line(b, c, color); Line(c, d, color); Line(d, a, color);
    }
}
