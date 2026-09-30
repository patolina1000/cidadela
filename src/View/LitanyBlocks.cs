using System.Collections.Generic;
using Cidadela.Simulation;
using Godot;

namespace Cidadela.View;

/// <summary>
/// A ladainha de um aldeão desenhada em BLOCOS, no estilo Scratch (docs/ladainhas.md, ajuste 3 do Arthur): um bloco por
/// comando, empilhados e encaixados (dente em cima, aba embaixo), cor por tipo de comando, o comando atual aceso e, se
/// travou, contornado em laranja com o motivo. Só para ver; o editor em blocos vai usar o mesmo desenho.
/// </summary>
public partial class LitanyBlocks : Control
{
    private const float BlockHeight = 34f, Gap = 2f, Notch = 12f, NotchDepth = 5f, NotchInset = 16f, Width = 420f;

    private SimWorld? _world;
    private Villager? _villager;
    private IReadOnlyList<LitanyCommand>? _recording;

    /// <summary>Mostra a ladainha do aldeão (o comando atual aceso).</summary>
    public void Show(SimWorld world, Villager? villager)
    {
        _world = world;
        _villager = villager;
        _recording = null;
        Resize(villager?.Litany?.Commands.Count ?? 0);
    }

    /// <summary>Mostra o que está sendo gravado (ensinar por demonstração), sem comando aceso.</summary>
    public void ShowRecording(SimWorld world, IReadOnlyList<LitanyCommand> commands)
    {
        _world = world;
        _recording = commands;
        Resize(commands.Count);
    }

    private void Resize(int count)
    {
        CustomMinimumSize = new Vector2(Width, (BlockHeight + Gap) * count + NotchDepth + 4f);
        QueueRedraw();
    }

    public override void _Process(double delta)
    {
        if (_villager is not null || _recording is not null)
            QueueRedraw(); // o comando atual muda sozinho; a gravação cresce
    }

    public override void _Draw()
    {
        IReadOnlyList<LitanyCommand>? commands = _recording ?? _villager?.Litany?.Commands;
        if (_world is null || commands is null)
            return;
        if (_recording is not null && CustomMinimumSize.Y < (BlockHeight + Gap) * commands.Count)
            Resize(commands.Count);
        Font font = ThemeDB.FallbackFont;
        for (int i = 0; i < commands.Count; i++)
        {
            LitanyCommand c = commands[i];
            bool current = _recording is null && i == _villager!.CommandIndex;
            float y = i * (BlockHeight + Gap);
            Color color = LitanyText.BlockColor(c.Verb);
            if (!current)
                color = color.Darkened(0.35f);
            Vector2[] shape = BlockShape(y);
            DrawColoredPolygon(shape, color);
            Color edge = current && _villager!.Stuck is not null ? Palette.Pumpkin : current ? Palette.Bone : color.Darkened(0.4f);
            var outline = new Vector2[shape.Length + 1];
            shape.CopyTo(outline, 0);
            outline[^1] = shape[0];
            DrawPolyline(outline, edge, current ? 3f : 1.5f, antialiased: true);
            string text = $"{i + 1}  {LitanyText.Command(c, _world)}";
            DrawString(font, new Vector2(12f, y + BlockHeight / 2f + 6f), text, HorizontalAlignment.Left, Width - 24f, 15,
                current ? Colors.White : new Color(1f, 1f, 1f, 0.8f));
            if (current)
                DrawString(font, new Vector2(Width - 22f, y + BlockHeight / 2f + 6f), "◀", HorizontalAlignment.Left, -1f, 15, Palette.Bone);
        }
    }

    /// <summary>O contorno de um bloco: retângulo com o dente de encaixe em cima e a aba embaixo.</summary>
    private static Vector2[] BlockShape(float y)
    {
        float top = y, bottom = y + BlockHeight;
        return new[]
        {
            new Vector2(0f, top), new Vector2(NotchInset, top), new Vector2(NotchInset + 4f, top + NotchDepth),
            new Vector2(NotchInset + Notch - 4f + 4f, top + NotchDepth), new Vector2(NotchInset + Notch + 4f, top),
            new Vector2(Width, top), new Vector2(Width, bottom),
            new Vector2(NotchInset + Notch + 4f, bottom), new Vector2(NotchInset + Notch - 4f + 4f, bottom + NotchDepth),
            new Vector2(NotchInset + 4f, bottom + NotchDepth), new Vector2(NotchInset, bottom), new Vector2(0f, bottom),
        };
    }
}
