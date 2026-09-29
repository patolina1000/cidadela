using System;
using System.Collections.Generic;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Atlas provisório do rosto do aldeão, desenhado por código enquanto a arte não entrega olhos.png e boca.png
/// (docs/aldeao_v2_contrato.md). Segue o formato do contrato: grade fixa, célula com margem transparente
/// dentro, índice 0 = quadro padrão. Símbolos simples e o número do quadro no canto, para conferir a troca de
/// célula na cena de teste.
/// </summary>
public static class FaceAtlasPlaceholder
{
    public const int EyesColumns = 4, EyesRows = 3, EyesCellWidth = 96, EyesCellHeight = 48;
    public const int MouthColumns = 3, MouthRows = 2, MouthCellWidth = 64, MouthCellHeight = 32;
    public const int Margin = 8;

    /// <summary>Quadros dos olhos, na ordem do atlas (0 = distraído, como pede o contrato; meio_fechado é do piscar).</summary>
    public static readonly string[] EyesFrames =
        { "distraido", "esforco", "feliz", "sonolento", "fechado", "espantado", "preocupado", "chorando", "bravo", "meio_fechado" };

    /// <summary>Quadros da boca, na ordem do atlas (0 = entreaberta).</summary>
    public static readonly string[] MouthFrames = { "entreaberta", "neutra", "sorriso", "esforco", "o", "triste" };

    private static readonly Color Ink = new("1B1E26");
    private static readonly Color White = new("E3E7EB");
    private static readonly Color Tear = new("7FB3D5");

    public static Dictionary<string, int> Frames(string[] names)
    {
        var map = new Dictionary<string, int>();
        for (int i = 0; i < names.Length; i++)
            map[names[i]] = i;
        return map;
    }

    public static Image EyesImage()
    {
        Image image = Image.CreateEmpty(EyesColumns * EyesCellWidth, EyesRows * EyesCellHeight, false, Image.Format.Rgba8);
        image.Fill(Colors.Transparent);
        for (int i = 0; i < EyesFrames.Length; i++)
        {
            int ox = i % EyesColumns * EyesCellWidth, oy = i / EyesColumns * EyesCellHeight;
            DrawEyes(image, ox, oy, EyesFrames[i]);
            Digit(image, ox + EyesCellWidth - Margin - 7, oy + Margin, i);
        }
        return image;
    }

    public static Image MouthImage()
    {
        Image image = Image.CreateEmpty(MouthColumns * MouthCellWidth, MouthRows * MouthCellHeight, false, Image.Format.Rgba8);
        image.Fill(Colors.Transparent);
        for (int i = 0; i < MouthFrames.Length; i++)
        {
            int ox = i % MouthColumns * MouthCellWidth, oy = i / MouthColumns * MouthCellHeight;
            DrawMouth(image, ox, oy, MouthFrames[i]);
            Digit(image, ox + MouthCellWidth - Margin - 7, oy + Margin, i);
        }
        return image;
    }

    private static void DrawEyes(Image img, int ox, int oy, string frame)
    {
        // Dois olhos centrados na área útil (a margem de 8 px fica transparente).
        int cy = oy + EyesCellHeight / 2;
        int[] xs = { ox + 30, ox + 66 };
        foreach (int cx in xs)
        {
            int side = cx == xs[0] ? -1 : 1; // -1 = olho esquerdo (na imagem)
            switch (frame)
            {
                case "distraido":
                    Eye(img, cx, cy, 9, 3);
                    break;
                case "esforco":
                    Disc(img, cx, cy, 9, Ink, (dx, dy) => Math.Abs(dy) <= 2); // apertado: um traço grosso
                    Disc(img, cx, cy - 8, 8, Ink, (dx, dy) => dy >= -1 && dy <= 1 && dx * side < 3); // sobrancelha tensa
                    break;
                case "feliz":
                    Disc(img, cx, cy + 3, 10, Ink, (dx, dy) => dy <= 0); // arco para cima
                    Disc(img, cx, cy + 3, 7, Colors.Transparent, (dx, dy) => dy <= 0);
                    break;
                case "sonolento":
                    Eye(img, cx, cy, 9, 3);
                    Disc(img, cx, cy - 3, 10, Ink, (dx, dy) => dy <= 0); // pálpebra caída
                    break;
                case "fechado":
                    Rect(img, cx - 9, cy - 1, 18, 3, Ink);
                    break;
                case "meio_fechado":
                    Eye(img, cx, cy, 9, 3);
                    Disc(img, cx, cy - 5, 11, Ink, (dx, dy) => dy <= 0); // pálpebra até o meio da pupila
                    break;
                case "espantado":
                    Eye(img, cx, cy, 12, 2);
                    break;
                case "preocupado":
                    Eye(img, cx, cy, 9, 3);
                    Line(img, cx + side * 10, cy - 12, cx - side * 4, cy - 15, 2, Ink); // sobrancelha erguida por dentro
                    break;
                case "chorando":
                    Eye(img, cx, cy, 9, 3);
                    Rect(img, cx - 1, cy + 9, 3, 6, Tear);
                    Disc(img, cx, cy + 16, 3, Tear);
                    break;
                case "bravo":
                    Eye(img, cx, cy, 9, 3);
                    Line(img, cx + side * 10, cy - 15, cx - side * 3, cy - 10, 2, Ink); // sobrancelha franzida por dentro
                    break;
            }
        }
    }

    private static void DrawMouth(Image img, int ox, int oy, string frame)
    {
        int cx = ox + MouthCellWidth / 2, cy = oy + MouthCellHeight / 2;
        switch (frame)
        {
            case "entreaberta":
                Disc(img, cx, cy, 6, Ink, (dx, dy) => Math.Abs(dy) <= 3);
                break;
            case "neutra":
                Rect(img, cx - 10, cy - 1, 20, 3, Ink);
                break;
            case "sorriso":
                Disc(img, cx, cy - 3, 10, Ink, (dx, dy) => dy >= 0);
                Disc(img, cx, cy - 3, 7, Colors.Transparent, (dx, dy) => dy >= 0);
                break;
            case "esforco":
                Rect(img, cx - 10, cy - 4, 20, 8, Ink);
                Rect(img, cx - 8, cy - 2, 16, 4, White);
                for (int x = cx - 5; x <= cx + 5; x += 5)
                    Rect(img, x, cy - 2, 1, 4, Ink);
                break;
            case "o":
                Disc(img, cx, cy, 7, Ink);
                Disc(img, cx, cy, 4, Colors.Transparent);
                break;
            case "triste":
                Disc(img, cx, cy + 5, 10, Ink, (dx, dy) => dy <= 0);
                Disc(img, cx, cy + 5, 7, Colors.Transparent, (dx, dy) => dy <= 0);
                break;
        }
    }

    /// <summary>Olho: contorno escuro, branco dentro e pupila.</summary>
    private static void Eye(Image img, int cx, int cy, int radius, int pupil)
    {
        Disc(img, cx, cy, radius, Ink);
        Disc(img, cx, cy, radius - 2, White);
        Disc(img, cx, cy, pupil, Ink);
    }

    private static void Disc(Image img, int cx, int cy, int radius, Color color, Func<int, int, bool>? keep = null)
    {
        for (int dy = -radius; dy <= radius; dy++)
            for (int dx = -radius; dx <= radius; dx++)
            {
                if (dx * dx + dy * dy > radius * radius || (keep is not null && !keep(dx, dy)))
                    continue;
                Put(img, cx + dx, cy + dy, color);
            }
    }

    private static void Rect(Image img, int x, int y, int w, int h, Color color)
    {
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
                Put(img, x + i, y + j, color);
    }

    private static void Line(Image img, int x0, int y0, int x1, int y1, int thickness, Color color)
    {
        int steps = Math.Max(Math.Abs(x1 - x0), Math.Abs(y1 - y0)) + 1;
        for (int s = 0; s <= steps; s++)
        {
            float t = (float)s / steps;
            Disc(img, (int)MathF.Round(x0 + (x1 - x0) * t), (int)MathF.Round(y0 + (y1 - y0) * t), thickness / 2, color);
        }
    }

    // Fonte 3×5 dos dígitos, desenhada em 2× (6×10 px).
    private static readonly string[] Digits =
    {
        "111101101101111", "010110010010111", "111001111100111", "111001111001111", "101101111001001",
        "111100111001111", "111100111101111", "111001001001001", "111101111101111", "111101111001111",
    };

    private static void Digit(Image img, int x, int y, int value)
    {
        string bits = Digits[value % 10];
        for (int j = 0; j < 5; j++)
            for (int i = 0; i < 3; i++)
                if (bits[j * 3 + i] == '1')
                    Rect(img, x + i * 2, y + j * 2, 2, 2, Ink);
    }

    private static void Put(Image img, int x, int y, Color color)
    {
        if (x >= 0 && y >= 0 && x < img.GetWidth() && y < img.GetHeight())
            img.SetPixel(x, y, color);
    }
}
