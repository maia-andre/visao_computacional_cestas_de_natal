# Fase 2 — Ensinar o modelo a ver cesta

**Objetivo:** um YOLO fine-tunado que detecta `cesta` e `palete` nas condições reais da operação, com mAP50 ≥ 0,85 no conjunto de validação.

## Por que fine-tuning e não "IA pronta"

O YOLO pré-treinado (COCO) sabe o que é pessoa, carro, garrafa. Não sabe o que é uma cesta de Natal embalada, nem um palete filmado. Fine-tuning = pegar esse modelo que já sabe "ver" e ensinar 2 classes novas com algumas centenas de exemplos nossos. É barato: **~300 imagens anotadas** dão um primeiro modelo utilizável.

## Passos

### 1. Extrair frames dos vídeos da Fase 1

Um frame a cada 1–2 segundos é suficiente (frames consecutivos são quase idênticos e não ensinam nada novo). Priorizar:

- a posição de câmera escolhida na Fase 1 (maior parte);
- a posição alternativa (para poder comparar na Fase 3);
- os piores casos: pico, mãos, cestas sobrepostas, pilhas, contraluz.

Meta inicial: **300–400 frames**, todos da tenda (ensaio + operação): bancada, paletes dentro do L, funcionário saindo, pilhas, entrega direta, pico.

### 2. Anotar

Ferramenta recomendada: **Roboflow** (roda no navegador, gratuito para projetos pequenos, exporta direto no formato YOLO). Alternativas locais: CVAT, Label Studio.

Classes:

| classe | o que marcar | o que **não** marcar |
|---|---|---|
| `cesta` | cada cesta individual visível — no palete (sem filme), na bancada, na mão do funcionário — mesmo parcialmente coberta | cestas dentro de palete filmado (não são distinguíveis) |
| `pilha2` | duas cestas empilhadas sendo carregadas juntas (uma caixa envolvendo as duas) | cestas empilhadas *paradas* no palete (essas são `cesta`, uma a uma, enquanto visíveis) |
| `palete` | o bloco inteiro (palete + carga) dentro da tenda | palete vazio (por enquanto) |

`pilha2` é uma aposta: só se justifica se o ensaio `ensaio_03_pilhas` mostrar que o detector de `cesta` vê 1 onde há 2. Se com câmera oblíqua ele já separar as duas, dispense a classe.

Regras de anotação (consistência importa mais que perfeição):
- Caixa justa ao objeto, sem folga.
- Cesta 50% coberta pela mão: marca. Cesta 90% coberta: não marca.
- Pessoas **não** são anotadas.

Dividir: 80% treino / 20% validação. Roboflow faz isso automaticamente.

### 3. Treinar

Onde:
- **Google Colab** (grátis, GPU T4): ~15 min para 300 imagens. Recomendado.
- Notebook sem GPU: 1–2 h. Funciona, só é lento.

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")               # começa do COCO
model.train(
    data="data/dataset/data.yaml",        # gerado pelo Roboflow
    epochs=60,
    imgsz=640,
    batch=16,
    patience=15,                          # para cedo se parar de melhorar
    project="runs", name="cestas_v1",
)
```

Resultado em `runs/cestas_v1/weights/best.pt`.

### 4. Avaliar

```python
metrics = YOLO("runs/cestas_v1/weights/best.pt").val(data="data/dataset/data.yaml")
print(metrics.box.map50)   # meta: >= 0.85
```

Olhar também `runs/cestas_v1/confusion_matrix.png` e as imagens `val_batch*_pred.jpg`: onde erra?

Se ficar abaixo de 0,85: **anotar mais** frames exatamente do tipo em que errou. Não mexer em hiperparâmetros antes de ter mais dados.

### 5. Plugar no pipeline

```powershell
.\rodar.cmd scripts\contar.py --fonte data\videos\ensaio_01_normal_obliqua.mp4 --modelo runs\cestas_v1\weights\best.pt --classes cesta pilha2 --zonas data\zonas\tenda.json
```

Nada mais muda no código.

## Escolha do tamanho do modelo

| modelo | velocidade CPU (i5, 640 px) | quando |
|---|---|---|
| yolov8**n** | ~15–25 fps | Padrão. Comece aqui. |
| yolov8**s** | ~8–12 fps | Se `n` errar em cestas pequenas/ocluídas e houver folga de CPU. |
| yolov8**m**+ | < 5 fps CPU | Só com GPU. Provavelmente desnecessário. |

Na tenda, uma cesta leva segundos para mudar de zona; 10 fps é sobra.

## Critério de conclusão

- [ ] ≥ 300 frames anotados, dataset exportado em formato YOLO em `data/dataset/`.
- [ ] `best.pt` com mAP50 ≥ 0,85 na validação.
- [ ] Matriz de confusão analisada; principais erros documentados aqui embaixo.
- [ ] Decidido se `pilha2` fica ou sai.
- [ ] `contar.py` rodando com `--modelo best.pt --classes cesta --zonas ...` num vídeo da tenda.

## Registro de erros observados

_(preencher durante a fase)_

| condição | sintoma | ação |
|---|---|---|
| | | |
