using System;
using System.Collections.Generic;

namespace Cidadela.Simulation;

/// <summary>
/// Busca de caminho A* na grade, em 8 direções, sem cortar quina (diagonal só se as duas laterais
/// estão livres). Custo 1 reto e √2 na diagonal; a estimativa é a distância octil até o objetivo mais perto.
/// </summary>
public static class GridPath
{
    private static readonly (int X, int Z)[] Steps =
    {
        (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1),
    };

    /// <summary>
    /// Células a percorrer de <paramref name="start"/> (exclusive) até um dos objetivos (inclusive).
    /// Lista vazia se já está num objetivo; null se nenhum é alcançável.
    /// </summary>
    public static List<GridPos>? Find(Func<GridPos, bool> isSolid, GridPos start, IReadOnlyCollection<GridPos> goals)
    {
        if (goals.Count == 0)
            return null;
        var goalSet = new HashSet<GridPos>(goals);
        if (goalSet.Contains(start))
            return new List<GridPos>();

        var open = new PriorityQueue<GridPos, float>();
        var cameFrom = new Dictionary<GridPos, GridPos>();
        var cost = new Dictionary<GridPos, float> { [start] = 0f };
        open.Enqueue(start, Estimate(start, goalSet));

        while (open.TryDequeue(out GridPos current, out _))
        {
            if (goalSet.Contains(current))
                return Rebuild(cameFrom, start, current);

            foreach ((int dx, int dz) in Steps)
            {
                var next = new GridPos(current.X + dx, current.Z + dz);
                if (isSolid(next))
                    continue;
                bool diagonal = dx != 0 && dz != 0;
                if (diagonal && (isSolid(new GridPos(current.X + dx, current.Z)) || isSolid(new GridPos(current.X, current.Z + dz))))
                    continue;

                float newCost = cost[current] + (diagonal ? 1.41421f : 1f);
                if (cost.TryGetValue(next, out float known) && known <= newCost)
                    continue;
                cost[next] = newCost;
                cameFrom[next] = current;
                open.Enqueue(next, newCost + Estimate(next, goalSet));
            }
        }
        return null;
    }

    private static float Estimate(GridPos from, HashSet<GridPos> goals)
    {
        float best = float.MaxValue;
        foreach (GridPos g in goals)
        {
            int dx = Math.Abs(g.X - from.X), dz = Math.Abs(g.Z - from.Z);
            best = Math.Min(best, Math.Max(dx, dz) + 0.41421f * Math.Min(dx, dz));
        }
        return best;
    }

    private static List<GridPos> Rebuild(Dictionary<GridPos, GridPos> cameFrom, GridPos start, GridPos end)
    {
        var path = new List<GridPos>();
        for (GridPos at = end; at != start; at = cameFrom[at])
            path.Add(at);
        path.Reverse();
        return path;
    }
}
