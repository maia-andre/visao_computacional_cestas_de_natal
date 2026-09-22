# Fase 2 — Ensinar o modelo a ver cesta

**Objetivo:** um YOLO fine-tunado que detecta `cesta` nas condições reais da operação, com mAP50 ≥ 0,85 no conjunto de validação.

## Por que fine-tuning e não "IA pronta"

O YOLO pré-treinado (COCO) sabe o que é pessoa, carro, garrafa. Não sabe o que é uma cesta de Natal embalada, nem um palete filmado. Fine-tuning = pegar esse modelo que já sabe "ver" e ensinar as classes novas com algumas centenas de exemplos nossos. É barato: **~300 imagens anotadas** dão um primeiro modelo utilizável.

Confirmado na prática em 2026-09-21: o `yolov8n.pt` base detecta as pessoas nos vídeos do almoxarifado, mas não as cestas (só um `suitcase` esporádico).

## Passos

### 1. Extrair frames dos vídeos da Fase 1

```powershell
.\rodar.cmd scripts\extrair_frames.py data\videos\2026-09-21_almox_obliqua_01.mp4 data\videos\2026-09-21_almox_obliqua_02.mp4
```

Um frame a cada 0,5 s (padrão), redimensionado para 1920 px no lado maior. Frames consecutivos são quase idênticos e não ensinam nada novo. Saída em `data/dataset/frames/<nome_do_video>/`.

Priorizar: a posição de câmera escolhida na Fase 1 (maior parte), a posição alternativa (para comparar na Fase 3) e os piores casos — pico, mãos, cestas sobrepostas, pilhas, contraluz.

Meta: **300–400 frames**. Estado atual: **213** (125 + 88 dos dois vídeos do almoxarifado).

### 2. Pré-anotar com YOLO-World (zero-shot)

Anotar 200+ frames do zero é o gargalo da fase. O atalho: um detector *open-vocabulary* desenha as caixas primeiro e o anotador só corrige.

```powershell
.\rodar.cmd scripts\preanotar.py --previa 5          # confere o resultado antes de enviar
.\rodar.cmd scripts\preanotar.py --token SEU_TOKEN   # envia como predictions pro Label Studio
```

O `preanotar.py` usa o **YOLO-World** (`yolov8s-worldv2.pt`), que aceita um prompt de texto em vez de classes fixas. Com o prompt `"box"` ele acha as cestas com confiança 0,32–0,61 e **separa a pilha de 2** — o que dispensa a classe `pilha2` se o comportamento se confirmar no resto dos frames.

Decisões embutidas no script, e o porquê:

| parâmetro | padrão | por quê |
|---|---|---|
| `--conf` | 0,05 | Confiança baixa de propósito: apagar uma caixa errada é mais rápido que desenhar uma que faltou. |
| `--ignorar-acima` | 0,30 | Descarta caixas com centro no terço superior do quadro — nesses vídeos é o fundo do galpão (paletes de papel, caixas de estoque), que não interessa. |
| `--largura-max` | 50 (% do quadro) | Descarta o balcão de OSB, que é ele próprio uma "box" para o YOLO-World. Ver abaixo. |

Resultado em 2026-09-22: 213 tarefas, **1.300 caixas, média 6,1/frame**, só 2 frames sem nenhuma caixa.

**Falso positivo principal — o balcão.** O balcão de OSB é ele próprio uma "box" para o YOLO-World. Na primeira rodada foram 227 caixas enormes (13–19% da imagem) em 176 dos 213 frames.

O que **não** separa esses falsos positivos: a **confiança**. Chega a 0,43, e 21 delas passavam de 0,30 — sobrepondo a faixa das cestas boas (0,32–0,61). Filtrar por confiança apagaria cesta de verdade.

O que separa: a **largura**. O balcão atravessa o quadro (46,5–65,8% da largura); uma cesta nunca passa de ~49%, nem carregada perto da câmera. Daí o `--largura-max 50`, que remove 224 das 230 caixas de balcão sem tocar em nenhuma cesta.

O corte foi posto em 50 e não em 45 de propósito: a 45% ele pegaria 6 balcões a mais, mas apagaria junto uma caixa frouxa que envolvia uma cesta real. Caixa apagada é cesta que o anotador pode não notar; caixa sobrando é um `Backspace`. Sobram ~6 balcões para apagar à mão em 213 frames.

**Falso positivo menor:** um pedaço de papelão achatado no chão é detectado como cesta (confiança ~0,05, aparece em boa parte dos frames). Apagar na anotação.

### 3. Anotar no Label Studio

Ferramenta: **Label Studio local** — não Roboflow, porque os frames mostram servidores da prefeitura e não devem subir para serviço de terceiros.

```powershell
.\anotar.cmd     # sobe em http://localhost:8080, projeto cesta_v1
```

O `anotar.cmd` existe porque o Label Studio precisa de `LOCAL_FILES_SERVING_ENABLED=true` e `LOCAL_FILES_DOCUMENT_ROOT` apontando para `data\dataset`; sem essas variáveis as tarefas abrem com as imagens quebradas. Ele roda no Python global, **não** no `.venv` do projeto.

Classes configuradas no projeto `cesta_v1`:

| classe | o que marcar | o que **não** marcar |
|---|---|---|
| `cesta` | cada cesta individual visível — no palete (sem filme), na bancada, na mão do funcionário — mesmo parcialmente coberta | cestas dentro de palete filmado (não são distinguíveis) |
| `palete` | o bloco inteiro (palete + carga) dentro da tenda | palete vazio (por enquanto) |

> **Decidido em 2026-09-22:** a classe `balcao` foi **removida**. As zonas de contagem são polígonos desenhados à mão uma vez (câmera fixa a partir da Fase 3), então detectar o balcão não ajuda a contar nada. A classe `pilha2` do plano original **não** foi criada — o YOLO-World já separa a pilha de 2, ver a nota no passo 2.

Regras de anotação (consistência importa mais que perfeição):

- Caixa justa ao objeto, sem folga.
- Cesta 50% coberta pela mão: marca. Cesta 90% coberta: não marca.
- Pessoas **não** são anotadas.
- **Nunca rotacionar a caixa** — ver abaixo.

#### Rotação: não use

O Label Studio permite girar um retângulo, mas a exportação YOLO padrão **descarta o ângulo em silêncio** (`convert_annotation_to_yolo`, no `label_studio_sdk/converter/utils.py`, usa só x/y/w/h — e o x/y que o LS guarda é o canto superior esquerdo *já rotacionado*). O resultado é uma caixa deslocada no dataset, sem nenhum aviso.

Caixas giradas só funcionam exportando em **YOLO-OBB**, o que exige treinar um modelo da família `yolov8n-obb.pt` e mudar o `src/cestas/pipeline.py`. Não é o caminho desta fase. Para uma cesta inclinada, desenhe o retângulo alinhado aos eixos que a envolve.

A alça de rotação já foi **desabilitada** no projeto `cesta_v1` para o erro não ser possível (Settings → Labeling Interface):

```xml
<RectangleLabels name="label" toName="image" canRotate="false">
```

Dividir: 80% treino / 20% validação.

### 4. Exportar

No Label Studio: **Export → YOLO**. Descompactar em `data/dataset/`, que deve ficar com `images/`, `labels/` e `data.yaml`.

Conferir no `data.yaml` que a ordem das classes bate com a que o `contar.py` vai usar.

### 5. Treinar

Onde:

- **Google Colab** (grátis, GPU T4): ~15 min para 300 imagens. Recomendado.
- Notebook sem GPU: 1–2 h. Funciona, só é lento.

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")               # começa do COCO
model.train(
    data="data/dataset/data.yaml",
    epochs=60,
    imgsz=640,
    batch=16,
    patience=15,                          # para cedo se parar de melhorar
    project="runs", name="cestas_v1",
)
```

Resultado em `runs/cestas_v1/weights/best.pt`.

### 6. Avaliar

```python
metrics = YOLO("runs/cestas_v1/weights/best.pt").val(data="data/dataset/data.yaml")
print(metrics.box.map50)   # meta: >= 0.85
```

Olhar também `runs/cestas_v1/confusion_matrix.png` e as imagens `val_batch*_pred.jpg`: onde erra?

Se ficar abaixo de 0,85: **anotar mais** frames exatamente do tipo em que errou. Não mexer em hiperparâmetros antes de ter mais dados.

### 7. Plugar no pipeline

```powershell
.\rodar.cmd scripts\contar.py --fonte data\videos\2026-09-21_almox_obliqua_01.mp4 --modelo runs\cestas_v1\weights\best.pt --classes cesta --zonas data\zonas\tenda.json
```

Nada mais muda no código. A contagem sai comparável com a verdade-terreno de `data/videos/verdade.csv` (10 e 7 cestas nos dois vídeos).

## Escolha do tamanho do modelo

| modelo | velocidade CPU (i5, 640 px) | quando |
|---|---|---|
| yolov8**n** | ~15–25 fps | Padrão. Comece aqui. |
| yolov8**s** | ~8–12 fps | Se `n` errar em cestas pequenas/ocluídas e houver folga de CPU. |
| yolov8**m**+ | < 5 fps CPU | Só com GPU. Provavelmente desnecessário. |

Na tenda, uma cesta leva segundos para mudar de zona; 10 fps é sobra.

## Critério de conclusão

- [x] Frames extraídos (213 de 300–400).
- [x] Pré-anotação zero-shot enviada para o Label Studio (213/213 tarefas).
- [ ] ≥ 300 frames anotados (corrigidos por humano), dataset exportado em formato YOLO em `data/dataset/`.
- [ ] `best.pt` com mAP50 ≥ 0,85 na validação.
- [ ] Matriz de confusão analisada; principais erros documentados aqui embaixo.
- [x] Decidido: `balcao` saiu. Falta confirmar se `pilha2` é dispensável ao longo da anotação.
- [ ] `contar.py` rodando com `--modelo best.pt --classes cesta --zonas ...` num vídeo do almoxarifado.

## Registro de erros observados

| condição | sintoma | ação |
|---|---|---|
| Pré-anotação YOLO-World, prompt `"box"` | O balcão de OSB é detectado como uma caixa gigante (13–19% da imagem), em 176 dos 213 frames | Resolvido por `--largura-max 50`. **Não** filtrar por confiança: a do balcão chega a 0,43 e invade a faixa das cestas |
| Pré-anotação YOLO-World, prompt `"box"` | Papelão achatado no chão detectado como cesta | Apagar na anotação |
| YOLOv8n base (COCO) | Não detecta cesta nenhuma; só `suitcase` esporádico | Motivo desta fase existir |
