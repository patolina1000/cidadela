using System;

namespace Cidadela.Simulation;

/// <summary>
/// Mundo de estresse para medir a escala prevista no GDD (milhares de inimigos, máquinas e itens em esteiras).
/// É orientado a dados: cada componente é um array (posição X, posição Z, alvo...), sem um objeto por entidade,
/// e o tick percorre os arrays em sequência. Formas: inimigos andam para pontos aleatórios do campo; itens
/// correm em circuitos retangulares de esteira; máquinas ficam paradas e só avançam um progresso.
/// Determinístico: mesmo <c>seed</c>, mesmas posições em cada tick.
/// </summary>
public sealed class StressWorld
{
    public const float EnemySpeed = 1.6f;   // células por segundo
    public const float ItemSpeed = 1.875f;  // células por segundo (esteira básica do Factorio)
    private const int BlockWidth = 16, BlockHeight = 8;   // cada bloco tem um circuito de esteira e 10 máquinas
    private const int LoopWidth = 14, LoopHeight = 6;

    public int Width { get; }
    public int Height { get; }
    public long TickCount { get; private set; }

    public int EnemyCount { get; }
    public float[] EnemyX { get; }
    public float[] EnemyZ { get; }
    public float[] EnemyPrevX { get; }
    public float[] EnemyPrevZ { get; }
    public float[] EnemyYaw { get; }
    public byte[] EnemyKind { get; }
    private readonly float[] _enemyTargetX, _enemyTargetZ;

    public int MachineCount { get; }
    public float[] MachineX { get; }
    public float[] MachineZ { get; }
    public float[] MachineProgress { get; }
    public byte[] MachineKind { get; }

    public int ItemCount { get; }
    public float[] ItemX { get; }
    public float[] ItemZ { get; }
    public float[] ItemPrevX { get; }
    public float[] ItemPrevZ { get; }
    public byte[] ItemKind { get; }
    private readonly int[] _itemLane;
    private readonly float[] _itemS;

    /// <summary>Circuitos de esteira: retângulos (x0, z0, largura, altura) em células; os itens correm no perímetro.</summary>
    public (int X0, int Z0, int W, int H)[] Lanes { get; }

    private uint _rng;

    public StressWorld(int width, int height, int enemies, int machines, int items, uint seed = 12345)
    {
        Width = width;
        Height = height;
        _rng = seed == 0 ? 1u : seed;

        // Circuitos e máquinas por bloco, do canto para dentro, até dar a quantidade pedida.
        int blocksX = width / BlockWidth, blocksZ = height / BlockHeight;
        var lanes = new System.Collections.Generic.List<(int, int, int, int)>();
        var machineCells = new System.Collections.Generic.List<(int x, int z)>();
        for (int bz = 0; bz < blocksZ; bz++)
        for (int bx = 0; bx < blocksX; bx++)
        {
            int x0 = bx * BlockWidth + 1, z0 = bz * BlockHeight + 1;
            lanes.Add((x0, z0, LoopWidth, LoopHeight));
            for (int mz = z0 + 2; mz <= z0 + LoopHeight - 2; mz += 2)
            for (int mx = x0 + 2; mx <= x0 + LoopWidth - 2; mx += 2)
                if (machineCells.Count < machines)
                    machineCells.Add((mx, mz));
        }
        Lanes = lanes.ToArray();

        MachineCount = machineCells.Count;
        MachineX = new float[MachineCount];
        MachineZ = new float[MachineCount];
        MachineProgress = new float[MachineCount];
        MachineKind = new byte[MachineCount];
        for (int i = 0; i < MachineCount; i++)
        {
            MachineX[i] = machineCells[i].x + 0.5f;
            MachineZ[i] = machineCells[i].z + 0.5f;
            MachineProgress[i] = NextFloat();
            MachineKind[i] = (byte)(i % 3);
        }

        EnemyCount = enemies;
        EnemyX = new float[enemies];
        EnemyZ = new float[enemies];
        EnemyPrevX = new float[enemies];
        EnemyPrevZ = new float[enemies];
        EnemyYaw = new float[enemies];
        EnemyKind = new byte[enemies];
        _enemyTargetX = new float[enemies];
        _enemyTargetZ = new float[enemies];
        for (int i = 0; i < enemies; i++)
        {
            EnemyX[i] = EnemyPrevX[i] = NextFloat() * width;
            EnemyZ[i] = EnemyPrevZ[i] = NextFloat() * height;
            EnemyKind[i] = (byte)(i % 4);
            PickTarget(i);
        }

        ItemCount = Lanes.Length == 0 ? 0 : items;
        ItemX = new float[ItemCount];
        ItemZ = new float[ItemCount];
        ItemPrevX = new float[ItemCount];
        ItemPrevZ = new float[ItemCount];
        ItemKind = new byte[ItemCount];
        _itemLane = new int[ItemCount];
        _itemS = new float[ItemCount];
        for (int i = 0; i < ItemCount; i++)
        {
            _itemLane[i] = i % Lanes.Length;
            _itemS[i] = NextFloat() * Perimeter(Lanes[_itemLane[i]]);
            ItemKind[i] = (byte)(i % 4);
            (ItemX[i], ItemZ[i]) = LanePoint(Lanes[_itemLane[i]], _itemS[i]);
            ItemPrevX[i] = ItemX[i];
            ItemPrevZ[i] = ItemZ[i];
        }
    }

    public void Tick()
    {
        float dt = (float)SimClock.TickSeconds;
        float enemyStep = EnemySpeed * dt;
        for (int i = 0; i < EnemyCount; i++)
        {
            EnemyPrevX[i] = EnemyX[i];
            EnemyPrevZ[i] = EnemyZ[i];
            float dx = _enemyTargetX[i] - EnemyX[i], dz = _enemyTargetZ[i] - EnemyZ[i];
            float dist = MathF.Sqrt(dx * dx + dz * dz);
            if (dist < enemyStep)
            {
                EnemyX[i] = _enemyTargetX[i];
                EnemyZ[i] = _enemyTargetZ[i];
                PickTarget(i);
                continue;
            }
            EnemyX[i] += dx / dist * enemyStep;
            EnemyZ[i] += dz / dist * enemyStep;
            EnemyYaw[i] = MathF.Atan2(-dx, -dz);
        }

        float itemStep = ItemSpeed * dt;
        for (int i = 0; i < ItemCount; i++)
        {
            ItemPrevX[i] = ItemX[i];
            ItemPrevZ[i] = ItemZ[i];
            var lane = Lanes[_itemLane[i]];
            float s = _itemS[i] + itemStep;
            float perimeter = Perimeter(lane);
            if (s >= perimeter)
            {
                s -= perimeter;
                // Deu a volta: a posição anterior não pode ficar do outro lado do circuito (senão o desenho
                // interpola atravessando o retângulo).
                (ItemPrevX[i], ItemPrevZ[i]) = LanePoint(lane, s);
            }
            _itemS[i] = s;
            (ItemX[i], ItemZ[i]) = LanePoint(lane, s);
        }

        float machineStep = 0.25f * dt;
        for (int i = 0; i < MachineCount; i++)
        {
            MachineProgress[i] += machineStep;
            if (MachineProgress[i] >= 1f)
                MachineProgress[i] -= 1f;
        }

        TickCount++;
    }

    /// <summary>Célula ocupada por esteira ou máquina (para a grama não nascer ali).</summary>
    public bool IsOccupied(GridPos cell)
    {
        foreach (var lane in Lanes)
        {
            bool onX = cell.X >= lane.X0 && cell.X <= lane.X0 + lane.W;
            bool onZ = cell.Z >= lane.Z0 && cell.Z <= lane.Z0 + lane.H;
            bool edgeX = cell.X == lane.X0 || cell.X == lane.X0 + lane.W;
            bool edgeZ = cell.Z == lane.Z0 || cell.Z == lane.Z0 + lane.H;
            if (onX && onZ && (edgeX || edgeZ))
                return true;
        }
        for (int i = 0; i < MachineCount; i++)
            if ((int)MachineX[i] == cell.X && (int)MachineZ[i] == cell.Z)
                return true;
        return false;
    }

    public static float Perimeter((int X0, int Z0, int W, int H) lane) => 2f * (lane.W + lane.H);

    /// <summary>Ponto no perímetro do circuito a <paramref name="s"/> células do canto, no sentido horário.</summary>
    public static (float x, float z) LanePoint((int X0, int Z0, int W, int H) lane, float s)
    {
        float cx = lane.X0 + 0.5f, cz = lane.Z0 + 0.5f;
        if (s < lane.W) return (cx + s, cz);
        s -= lane.W;
        if (s < lane.H) return (cx + lane.W, cz + s);
        s -= lane.H;
        if (s < lane.W) return (cx + lane.W - s, cz + lane.H);
        s -= lane.W;
        return (cx, cz + lane.H - s);
    }

    private void PickTarget(int i)
    {
        _enemyTargetX[i] = 0.5f + NextFloat() * (Width - 1f);
        _enemyTargetZ[i] = 0.5f + NextFloat() * (Height - 1f);
    }

    // xorshift32: rápido e determinístico, sem depender da implementação do Random do .NET.
    private float NextFloat()
    {
        _rng ^= _rng << 13;
        _rng ^= _rng >> 17;
        _rng ^= _rng << 5;
        return (_rng & 0xFFFFFF) / 16777216f;
    }
}
