using System;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Algo que a câmera cinematográfica pode focar: o nó desenhado, a altura do ponto olhado, a distância
/// inicial e uma descrição ao vivo (atualizada a cada frame, para mostrar o que o alvo está fazendo).
/// </summary>
public sealed record FocusTarget(Node3D Node, float Height, float Distance, Func<string> Describe);
