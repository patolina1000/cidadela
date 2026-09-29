# INVENTÁRIO DA PROTAGONISTA V1 — o que depende dela antes da v2

Levantado em 29/09/2026 no commit `b45b178` da `master`. A v1 está preservada na tag anotada
`protagonista-v1-arquivado` (commit `77b617c`). Nada da v1 foi mudado: ela continua no jogo até a v2 ficar pronta.

A simulação (`src/Simulation/Castellan.cs`, `CastellanStats.cs`, comandos e testes) **não conhece o modelo**.
Tudo que depende da v1 está na view, em dois JSON e nas cenas que instanciam `CastellanVisual`.

## 1. ARQUIVOS DA V1

| Arquivo | Papel |
|---|---|
| `assets/modelos/protagonista/protagonista.glb` | Modelo, rig e clipes (Meshy). ~1 MB. |
| `assets/modelos/protagonista/protagonista.json` | Só `{ "passada_run_m_s": 2.421 }`. |
| `assets/modelos/protagonista/protagonista_texture_0.png` | Textura de cor do corpo (material `Material_1`). |
| `assets/modelos/protagonista/protagonista_protagonista_cristal_emissao.png` | Emissão do material `Cristal`. |
| `assets/conceitos/protagonista.jpg`, `_frente.png`, `_costas.png` | Conceitos. |
| `assets/previews/protagonista_comparacao.png` | Prévia de comparação. |
| `docs/prints/biografia_protagonista.png` | Print da entrada na Biografia. |
| `src/View/CastellanVisual.cs` | Todo o desenho da protagonista. |
| `data/castellan.json` | Atributos do Castelão (a `speed` foi escolhida pela passada da v1). |

Os caminhos ficam fixos em `CastellanVisual.cs`: `ModelPath` e `ModelInfoPath` (linhas 18–19).

## 2. O GLB DA V1 (cabeçalho JSON)

- Uma malha, `char1`, com 2 primitivas e **2.974 triângulos**. Altura ~0,75 m; frente para +Z.
- Materiais: `Material_1` (corpo, textura de cor) e `Cristal` (textura de cor e de emissão).
  **Não usa o shader toon** dos aldeões: fica com o `StandardMaterial3D` do importador.
- Clipes: `attack`, `idle`, `run`, `work`, **sem** sufixo `-loop`. O loop é ligado no código.
- Importação com as opções padrão do Godot (nenhum `_subresources`, materiais não extraídos).
- Esqueleto de **24 ossos** (rig do Meshy).

### Ossos: v1 × `aldeao_corpo.glb` (branch `arte`, commit `745820e`)

**Iguais em nome, ordem e hierarquia** (conferido os 24, índice a índice, e o pai de cada um):

```
 0 Hips          6 RightLeg       12 LeftShoulder   18 RightForeArm
 1 LeftUpLeg     7 RightFoot      13 LeftArm        19 RightHand
 2 LeftLeg       8 RightToeBase   14 LeftForeArm    20 neck
 3 LeftFoot      9 Spine02        15 LeftHand       21 Head
 4 LeftToeBase  10 Spine01        16 RightShoulder  22 head_end
 5 RightUpLeg   11 Spine          17 RightArm       23 headfront
```

Hierarquia: `Hips` → pernas e `Spine02` → `Spine01` → `Spine` → ombros e `neck` → `Head` → `head_end`, `headfront`.
Atenção ao nome: no Meshy, `Spine` é o osso **de cima** da coluna (o do peito); `Spine02` é o de baixo.
A v1 prende o cristal em `Spine`; o `rosto.json` do aldeão registra `Spine02` como `ossoPeito`.
As poses de repouso não foram comparadas (as proporções dos corpos são diferentes).

## 3. CLIPES E ONDE SÃO USADOS

| Clipe | Onde |
|---|---|
| `idle`, `run`, `work` | `CastellanVisual._Ready` (linhas 56–62): ligados em loop linear; começa em `idle`. |
| `idle`, `run`, `work` | `CastellanVisual.UpdateFrom` (linha 113): `work` se há `GatherTarget`, `run` se andou no quadro, senão `idle`; mistura de 0,15 s. |
| `idle`, `run`, `work` | `data/biography.json`, entrada `protagonista`: `"animacoes": ["idle", "run", "work"]` (botões do palco). |
| qualquer um | `CastellanVisual.PlayClip` (linha 78), chamado por `BiographyRoot.PlayAnimation` (linha 444): toca em 1× fora da simulação. |
| `idle` | `MenuRoot` (linha 44): protagonista parada no centro do menu inicial. |
| `attack` | **Não usado** em lugar nenhum (existe só no GLB). |

O golpe de coleta **sem modelo** (`CastellanVisual.SwingAngle`) é reaproveitado pelo aldeão em
`VillagerVisual.cs:294`. Se a v2 mudar ou tirar a cápsula de reserva, o `SwingAngle` precisa continuar existindo
(ou mudar de lugar).

## 4. VELOCIDADE × PASSADA

- `data/castellan.json`: `"speed": 2.4` células/s. O comentário diz que 2,4 foi escolhido para bater com a passada
  natural do `run` da v1, **2,421 m/s**, gravada em `protagonista.json` como `passada_run_m_s`.
- `CastellanVisual.ReadStride` lê essa chave; `UpdateFrom` (linhas 117–123) toca o `run` a
  (distância andada ÷ dt ÷ passada), suavizado. Com a v1, isso dá ~1,0×.
- A chave da v1 é `passada_run_m_s` (snake_case); a do aldeão v2 é `passadaRun`, dentro do `rosto.json`.
- Nos testes, `TestWorlds.CastellanStats` usa `speed` 6.0 (fixo, não lê o JSON real).

## 5. CRISTAL E LUZ (`CastellanVisual.AddCrystalGlow`, linhas 146–186)

- Procura, em todas as malhas do modelo, a superfície cujo material é um `StandardMaterial3D` com
  `ResourceName == "Cristal"`. Duplica e multiplica `EmissionEnergyMultiplier` por **3** (`CrystalEmissionBoost`).
  Depende de o material se chamar exatamente `Cristal` e de ser `StandardMaterial3D`.
- `OmniLight3D` "CrystalLight": cor (0,35; 0,55; 1), energia 0,85, alcance 2,3, atenuação 1,4, sem sombra,
  especular 0,1.
- Presa ao osso **`Spine`** (`ChestBone`) por um `BoneAttachment3D` "Chest". Sem esse osso, fica a 0,55 m do chão.
- **Camada própria:** toda `MeshInstance3D` do modelo vai para `SelfLayer = 1u << 19` (camada 20); a luz usa
  `LightCullMask = ~SelfLayer`, então clareia o chão e os vizinhos e não o corpo dela. Nenhum outro arquivo usa a
  camada 20.

## 6. QUEM USA A POSIÇÃO OU O TAMANHO DELA

| Onde | O quê |
|---|---|
| `WorldView.cs:84–85, 127` | Cria o `CastellanVisual` e chama `UpdateFrom` a cada quadro. |
| `WorldView.cs:128` → `GrassField.SetPusher` → `Grass.gdshader` | A grama se inclina para longe dela: `pusher_pos` = posição global; `push_radius` 0,45 células, `push_strength` 0,08, e abaixa até 40% da altura. Usa só a posição, não o modelo. |
| `GrassField.cs:31` | Altura da grama (0,08–0,13) escolhida como ~20% dos 0,75 m da v1 (só comentário e constantes). |
| `WorldView.cs:233, 464` → `Effects.FlyTo` | Itens coletados voam até ela, mirando 0,9 m acima dos pés (`Effects.cs`, linha 88). |
| `WorldView.cs:342–343, 361` | Foco da câmera cinematográfica: altura 0,8 m, distância 3,2. |
| `WorldView.cs:363–368` | `AnimatedNodes`: entra na busca do alvo mais próximo do clique. |
| `GameRoot.cs:70` | A câmera segue `CastellanNode`. |
| `BiographyRoot.cs:183–186` | Palco: altura do alvo 0,42 m, distância 2,4. `BiographyRoot.cs:264` esconde o Castelão do mundo da máquina. |
| `MenuRoot.cs:41–50` | Menu: no centro, virada para a câmera; a câmera fica a +1,05 m e 3,8 m, enquadrada para a altura da v1. |
| `docs/aldeao_v2_contrato.md` | Escala do aldeão: 0,40 m, "bate na cintura da protagonista, que tem ~0,75 m". |
| `CastellanVisual.cs:68–74` | Cápsula de reserva (1,2 m, roxa, nariz laranja) quando falta o GLB. |

Nenhuma cena `.tscn` referencia o GLB ou o `CastellanVisual`: todos são criados por código.

## 7. SIMULAÇÃO E TESTES QUE TOCAM O CASTELÃO

Não dependem do modelo; só dos atributos de `castellan.json` (`speed`, `reach`, `gatherReach`, `radius`) e da
posição inicial no mapa (`data/maps/mapa_teste.json`, `"castellan": { "x": 15, "z": 16 }`).

- `GameData.Parse` valida `castellan.json` (`speed` positivo).
- `TestWorlds.CastellanStats` (JSON fixo, `speed` 6.0) alimenta quase todos os testes.
- `DataTests` e `VillagerSpeedTests` leem o `data/castellan.json` **real**.
- Testes que usam o Castelão (inventário, alcance, coleta, colisão, direção): `BuildTests`, `BeltTests`,
  `GatherTests`, `MachineTests`, `VillagerTests`, `SpawnItemTests`, `DataTests`, `TerrainTests`,
  `VillagerSpeedTests`.

## 8. O QUE A V2 VAI PRECISAR SUBSTITUIR

1. **O GLB** em `assets/modelos/protagonista/` (ou um caminho novo, como `protagonista_v2/`) e as constantes
   `ModelPath` e `ModelInfoPath` de `CastellanVisual.cs`.
2. **A passada:** o JSON da v2 com a passada do `run`, e a chave que `ReadStride` lê (`passada_run_m_s` hoje;
   alinhar com o `passadaRun` do aldeão se o formato mudar).
3. **`speed` em `data/castellan.json`** e o comentário dele, se a passada da v2 for diferente de 2,421 m/s. Os
   testes que leem o JSON real só exigem `speed` positivo.
4. **Clipes:** a v2 precisa de `idle`, `run` e `work` (os nomes que o código e a Biografia usam). Se vierem com
   `-loop`, o Godot tira o sufixo e o código pode deixar de forçar o loop. `attack` pode sair.
5. **`data/biography.json`:** a lista de `animacoes` da entrada `protagonista`, se os clipes mudarem.
6. **O cristal:** material chamado `Cristal` (ou mudar a busca em `AddCrystalGlow`), o multiplicador de emissão
   e o osso da luz (`Spine`). Se a v2 usar o shader toon, a busca por `StandardMaterial3D` e o reforço da
   emissão precisam ser refeitos para o material novo.
7. **A camada `SelfLayer`:** continua valendo se o modelo novo tiver as mesmas `MeshInstance3D`; se a v2 ganhar
   partes separadas (cabelo, rosto por retalhos, acessórios), todas precisam ir para a camada 20.
8. **Enquadramentos pela altura:** foco da câmera (0,8 m e 3,2), palco da Biografia (0,42 m e 2,4), câmera do
   menu (1,05 m e 3,8) e o alvo dos itens voando (0,9 m), se a altura mudar de ~0,75 m.
9. **A escala relativa:** a altura da grama e a regra "aldeão bate na cintura da protagonista" no contrato do
   aldeão, se a v2 não tiver ~0,75 m.
10. **Os documentos:** `docs/prints/biografia_protagonista.png`, a prévia de comparação e o texto da seção 20 do
    GDD que descrever o visual.
11. **A cápsula de reserva** e o `SwingAngle`: decidir se continuam (o aldeão usa o `SwingAngle`).
