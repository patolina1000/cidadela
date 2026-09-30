"""Região do couro cabeludo da protagonista v2 (a mesma na extração do cabelo e no teste de pele à mostra).

Couro cabeludo ("do topo da testa para trás") = as faces da malha "cabeca" do corpo em repouso que não são o rosto nem as
laterais do rosto: acima da linha do cabelo (topo da janela dos olhos + HAIRLINE da distância até o topo da cabeça) fora dos
±FACE_HALF_DEG da frente; nas laterais (até BACK_DEG), só da altura do meio dos olhos para cima (mandíbula e bochecha não
são couro cabeludo); atrás (além de BACK_DEG), até a nuca. A faixa de baixo da malha da cabeça (pescoço) fica de fora.
"""

import math

import numpy as np

HAIRLINE = 0.20
FACE_HALF_DEG = 60
BACK_DEG = 110
NECK_BAND = 0.012  # m acima do começo da malha da cabeça que ainda é pescoço


def hairline_z(eye_top_z, head_top_z):
    return eye_top_z + HAIRLINE * (head_top_z - eye_top_z)


def scalp_mask(points, center, eye_top_z, head_top_z, head_bottom_z, shrink=0.0, eye_mid_z=None, neck_drop=0.0):
    """Pontos (N×3, mundo, repouso) que são couro cabeludo. `shrink` recua a borda (m) para o teste não contar a própria
    linha do cabelo como pele à mostra. `eye_mid_z` e `neck_drop` deixam a calota descer mais que o teste nas laterais e na nuca."""
    p = np.asarray(points)
    hz = hairline_z(eye_top_z, head_top_z) + shrink
    ang = np.degrees(np.abs(np.arctan2(p[:, 0] - center[0], -(p[:, 1] - center[1]))))
    face = (ang <= FACE_HALF_DEG + math.degrees(shrink / 0.06)) & (p[:, 2] < hz)
    mid = eye_top_z - 0.02 if eye_mid_z is None else eye_mid_z
    side_low = (ang <= BACK_DEG + math.degrees(shrink / 0.06)) & (p[:, 2] < mid + shrink)
    neck = p[:, 2] < head_bottom_z + NECK_BAND + shrink - neck_drop
    return ~face & ~side_low & ~neck
