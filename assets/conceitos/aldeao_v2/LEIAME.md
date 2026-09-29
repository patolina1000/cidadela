# Aldeão v2 — folhas de modelagem

Entrada do aldeão novo. O contrato arte × jogo é `docs/aldeao_v2_contrato.md` (na `master`); o que sai daqui
vai para `assets/modelos/aldeao_v2/`. Nada é gerado na Meshy sem as folhas aqui e o custo aprovado.

## Pastas

- `folhas/`: as folhas do ChatGPT como vieram (corpo careca e sem rosto em T-pose ou A-pose: frente, lado e
  costas; cada peruca: frente e costas). Nomes sugeridos: `corpo.png`, `cabelo_1.png` … `cabelo_5.png`.
- `vistas/`: saída de `tools/arte/aldeao_v2/preparar_vistas.py`: cada vista recortada, centrada num quadrado de
  1024 px com margem e fundo liso, na mesma escala dentro da folha. Uma prévia `_previa_<folha>.png` por folha.
- `meshy/`: os GLB de teste baixados da Meshy (Parte C), antes de qualquer limpeza.

## Regras (lições do v1)

- Nunca recortar rostos de ilustrações: o rosto é o atlas desenhado por código (`desenhar_rosto.py`).
- A imagem enviada à Meshy precisa parecer um boneco 3D, com luz uniforme e fundo liso. Nas folhas: sem texto,
  setas, cabeças soltas ou fundo desenhado; frente, lado e costas na mesma escala.
- Corpo com a cabeça lisa (sem olhos, nariz ou boca); perucas como volume fechado, franja acima da sobrancelha.

## Como rodar o preparador

```
cd tools/arte
uv run aldeao_v2/preparar_vistas.py                                   # todas as folhas, vistas frente,lado,costas
uv run aldeao_v2/preparar_vistas.py --folha cabelo_1.png --vistas frente,costas
uv run aldeao_v2/preparar_vistas.py --folha corpo.png --vistas frente:1,lado:2,costas:3   # escolher por índice
uv run aldeao_v2/preparar_vistas.py --folha corpo.png --recorte 150,90,1180,660          # só uma região
```

Se a folha tiver figuras a mais (textos grandes, poses extras), o script lista as caixas encontradas e sai como
`vista_N`; escolha com `nome:índice`.
