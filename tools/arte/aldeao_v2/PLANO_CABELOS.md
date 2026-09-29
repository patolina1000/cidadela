# Plano das perucas do aldeão v2 (sem gerar nada ainda)

Entrada: 5 folhas do ChatGPT em `assets/conceitos/aldeao_v2/folhas/`, cada uma com 4 vistas (frente, lado ou 3/4,
costas, topo) já recortadas em `vistas/` pelo `preparar_vistas.py`. Todas desenham o cabelo **sobre uma cabeça**, e
essas cabeças são mais redondas e mais largas que a cabeça do corpo (corpo: largura/altura 0,93, ovo mais largo em
cima; cabelos 1 e 2 quase esféricos, 3 e 4 um pouco mais ovais, 5 esférica). Saída pelo contrato:
`assets/modelos/aldeao_v2/cabelos/cabelo_N.glb`, uma malha cada, ≤ 800 triângulos, material "cabelo", rígida, no
espaço do corpo em pose de repouso, sem cobrir o retalho "Olhos".

## 1. Gerar cabeça + cabelo na Meshy (20 créditos cada)

- Multi-Image to 3D com frente, lado e costas (a de topo entra como 4ª imagem só se a de 3 der o topo errado).
- `should_texture: false`, `should_remesh: true`, `topology: triangle`, `symmetry_mode: auto`, sem `pose_mode`.
- `target_polycount` **3000** para o conjunto cabeça + cabelo: a cabeça leva uns 40% disso e some depois; o
  cabelo sai com ~1.800 e é decimado para ≤ 800 no Blender (decimar depois é melhor do que pedir pouco à Meshy,
  que arredonda as pontas quando o alvo é baixo).
- Brutos em `assets/conceitos/aldeao_v2/meshy/cabelo_N_<tentativa>.glb`. Trava: 8 gerações no total (5 + 3
  repetições); estimativa 100 a 160 créditos.

## 2. Tirar a cabeça e ficar só com a peruca (`extrair_peruca.py`, Blender headless, a escrever)

Só geometria, porque o modelo vem sem cor (e a folha 5 nem tem contraste):

1. **Alinhar**: frente para -Y do Blender (+Z do glTF), topo para cima, centro na origem; escala pela altura da
   cabeça gerada (o rosto visível vai do topo até ~90% da silhueta na frente; o pescoço não existe nas folhas).
2. **Achar a cabeça dentro do modelo**: ajustar um elipsoide (centro + 3 raios, mínimos quadrados) aos vértices da
   **frente lisa** do modelo (o rosto sem cabelo, que é a única parte garantidamente "cabeça"). Esse elipsoide é a
   cabeça da folha.
3. **Classificar faces**: face cujo centro fica a mais de ~2 mm (na escala do jogo) fora do elipsoide é cabelo;
   o resto é cabeça e sai. O que sobra é uma casca aberta por baixo (a Meshy só modela a superfície de fora; o
   lado de dentro do cabelo nunca existiu). Da câmera do jogo isso não aparece; a borda da linha do cabelo fica
   fina em 3/4 e, se incomodar, fecha-se com uma faixa de 1 anel de faces para dentro (como a "touca" do v1, mas
   só na borda).
4. **Levar para a cabeça do corpo**: ajustar o mesmo tipo de elipsoide à cabeça do **corpo aprovado** (vértices
   acima do pescoço, medidos pelo `render_corpo.py`) e aplicar à peruca a transformação afim que leva um elipsoide
   no outro (escala por eixo + translação). A peruca acompanha a diferença de formato (a cabeça em ovo estica o
   cabelo um pouco na vertical e o estreita embaixo). Depois, todo vértice da peruca que ficar dentro da cabeça do
   corpo é empurrado para a superfície + 1,5 mm pela normal da cabeça (BVH, como o `fit_hair.py` do v1 na tag
   `aldeao-v1-arquivado`, que tem o empurrar, o fechar buracos e a abertura do rosto prontos para reaproveitar).
5. **Retalho "Olhos"**: a janela dos olhos no corpo é conhecida (fração da caixa da cabeça: x 3% a 97%, y 28% a
   83% do topo). Face de cabelo cujo centro projeta dentro dessa janela, na frente da cabeça, é apagada e a borda
   é refeita. **Isso muda o visual dos cabelos 2 e 3**, cuja franja cai até a altura dos olhos de um lado: vão
   ficar com a franja terminando na linha de cima da janela nesse lado. Alternativa: manter a franja e estreitar
   o retalho dos olhos naquele lado (decisão do Arthur; o contrato diz que nenhum cabelo cobre o retalho).
6. **Decimar** para ≤ 800 triângulos (Decimate por colapso, preservando bordas), medindo o erro de silhueta na
   câmera do jogo (render antes/depois a 48 px). Orçamento por cabelo:
   - 1 curto bagunçado: ~24 mechas em folha; cada ponta precisa de ~24 triângulos para não virar bolota → ~580
     nas mechas + ~150 na calota = ~730. É o mais apertado; se as pontas quebrarem, a saída é fundir as mechas
     pequenas de trás (que não leem de cima) antes de decimar. Se mesmo assim não couber, perguntar antes de
     passar de 800.
   - 2 chanel com franja: formas grandes, ~500 bastam.
   - 3 ondulado: ondas largas, ~600.
   - 4 longo liso: ~450, mais as pontas de baixo, que ficam **abaixo do queixo** e vão se mover com a cabeça
     como bloco rígido (o contrato pede rígido; anotar na prévia se parecer duro demais na caminhada).
   - 5 rabo de cavalo: calota ~300 + rabo ~250.
7. **Exportar**: uma malha, material "cabelo" (cor chapada), sem armature, no espaço do corpo em pose de repouso,
   `cabelo_N.glb`. O jogo prende no encaixe "Cabelo" compensando a pose do osso da cabeça.
8. **Conferir**: prévia dos 5 sobre o corpo a 55° em 256 e 48 px; teste automático de que nenhuma face fica
   dentro da janela dos olhos nem dentro da cabeça.

## 3. Folha do rabo de cavalo (5)

Recomendo **refazer no ChatGPT**, com o cabelo na mesma cor azul-acinzentada escura das outras folhas e a calota
um pouco mais grossa. Motivos: a Meshy não precisa da cor, mas a folha sem contraste tende a virar uma cabeça com
o rabo colado e sulcos rasos, e no passo 3 a calota quase rente (menos de 2 mm) seria classificada como cabeça e
sumiria, sobrando só o rabo e as faixas em relevo. Custa uma geração no ChatGPT contra 20 créditos e retrabalho.

## 4. Ordem

Corpo aprovado → gerar os 5 (1 tentativa cada) → `extrair_peruca.py` no mais simples (2 ou 4) para acertar o
método → os outros → prévia conjunta → decisão da franja de 2 e 3 → entrega.
