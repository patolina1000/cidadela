using System;
using System.Collections.Generic;
using System.Numerics;

namespace Cidadela.Simulation;

/// <summary>
/// Forma que um recurso bloqueia no chão: círculos (o tronco da árvore) e/ou um polígono convexo (a base da pedra ou do
/// veio, medida no GLB). Em coordenadas do modelo (metros, origem no centro da célula) até <see cref="Placed"/>, que gira,
/// escala e leva para a célula (coordenadas da simulação, como a posição do Castelão).
/// </summary>
public sealed class ResourceShape
{
    public IReadOnlyList<(Vector2 Center, float Radius)> Circles { get; }

    /// <summary>Polígono convexo em sentido anti-horário (vazio se não tem).</summary>
    public IReadOnlyList<Vector2> Polygon { get; }

    public ResourceShape(IReadOnlyList<(Vector2, float)> circles, IReadOnlyList<Vector2> polygon)
    {
        Circles = circles;
        Polygon = polygon;
    }

    /// <summary>Centro da forma: média dos vértices do polígono, ou dos centros dos círculos.</summary>
    public Vector2 Centroid
    {
        get
        {
            var sum = Vector2.Zero;
            int n = 0;
            foreach (Vector2 p in Polygon) { sum += p; n++; }
            if (n == 0)
                foreach ((Vector2 c, float _) in Circles) { sum += c; n++; }
            return n > 0 ? sum / n : Vector2.Zero;
        }
    }

    /// <summary>Girada (radianos, como o giro em Y do modelo na cena), escalada e posta no centro <paramref name="center"/>.</summary>
    public ResourceShape Placed(Vector2 center, float yaw, float scale)
    {
        float c = MathF.Cos(yaw), s = MathF.Sin(yaw);
        // Mesmo giro da cena: Basis(Up, yaw) leva (x, z) para (x·cos + z·sen, −x·sen + z·cos).
        Vector2 Map(Vector2 p) => center + new Vector2(p.X * c + p.Y * s, -p.X * s + p.Y * c) * scale;
        var circles = new List<(Vector2, float)>();
        foreach ((Vector2 cc, float r) in Circles)
            circles.Add((Map(cc), r * scale));
        var polygon = new List<Vector2>();
        foreach (Vector2 p in Polygon)
            polygon.Add(Map(p));
        return new ResourceShape(circles, polygon);
    }

    /// <summary>Distância com sinal de um ponto até a borda (negativa dentro), e o ponto da borda mais perto.</summary>
    public float SignedDistance(Vector2 p, out Vector2 closest, out Vector2 outward)
    {
        float best = float.MaxValue;
        closest = p;
        outward = Vector2.UnitX;
        foreach ((Vector2 c, float r) in Circles)
        {
            Vector2 d = p - c;
            float len = d.Length();
            Vector2 n = len > 1e-6f ? d / len : Vector2.UnitX;
            float sd = len - r;
            if (sd < best)
            {
                best = sd;
                closest = c + n * r;
                outward = n;
            }
        }
        if (Polygon.Count >= 3)
        {
            bool inside = true;
            float edgeBest = float.MaxValue;
            Vector2 q = p, n = Vector2.UnitX;
            for (int i = 0; i < Polygon.Count; i++)
            {
                Vector2 a = Polygon[i], b = Polygon[(i + 1) % Polygon.Count];
                Vector2 e = b - a;
                if (e.X * (p.Y - a.Y) - e.Y * (p.X - a.X) < 0f)
                    inside = false;
                float t = Math.Clamp(Vector2.Dot(p - a, e) / e.LengthSquared(), 0f, 1f);
                Vector2 onEdge = a + e * t;
                float d = Vector2.Distance(p, onEdge);
                if (d < edgeBest)
                {
                    edgeBest = d;
                    q = onEdge;
                    // Anti-horário: a normal para fora é (e.Y, −e.X).
                    n = Vector2.Normalize(new Vector2(e.Y, -e.X));
                }
            }
            float sd = inside ? -edgeBest : edgeBest;
            if (sd < best)
            {
                best = sd;
                closest = q;
                outward = inside || edgeBest < 1e-6f ? n : Vector2.Normalize(p - q);
            }
        }
        return best;
    }

    public float SignedDistance(Vector2 p) => SignedDistance(p, out _, out _);

    /// <summary>Empurra um corpo de raio <paramref name="radius"/> para fora da forma (desliza pela borda e pelas quinas).</summary>
    public Vector2 PushOut(Vector2 p, float radius)
    {
        float sd = SignedDistance(p, out Vector2 closest, out Vector2 outward);
        return sd >= radius ? p : closest + outward * radius;
    }

    /// <summary>Lê um polígono (pontos x, z) e o deixa anti-horário; recusa se não for convexo.</summary>
    public static List<Vector2> ConvexPolygon(IReadOnlyList<Vector2> points)
    {
        var list = new List<Vector2>(points);
        float area = 0f;
        for (int i = 0; i < list.Count; i++)
        {
            Vector2 a = list[i], b = list[(i + 1) % list.Count];
            area += a.X * b.Y - b.X * a.Y;
        }
        if (area < 0f)
            list.Reverse();
        for (int i = 0; i < list.Count; i++)
        {
            Vector2 a = list[i], b = list[(i + 1) % list.Count], c = list[(i + 2) % list.Count];
            if ((b.X - a.X) * (c.Y - b.Y) - (b.Y - a.Y) * (c.X - b.X) < -1e-6f)
                throw new FormatException("polígono de bloqueio precisa ser convexo.");
        }
        return list;
    }
}
