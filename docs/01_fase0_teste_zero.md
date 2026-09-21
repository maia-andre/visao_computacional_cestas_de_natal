# Fase 0 — Teste zero

**Objetivo:** ver o pipeline inteiro (detecção → tracking → linha virtual → evento no banco) funcionando **antes** de gravar qualquer vídeo ou comprar qualquer câmera.

Usa o YOLO pré-treinado no dataset COCO (80 classes: pessoa, carro, mochila, garrafa…). Ele **não conhece "cesta de Natal"** — isso é a Fase 2. Aqui o ponto é entender o encanamento.

## Precisa de

- Notebook com Python 3.10+ (sem GPU serve).
- Internet na primeira execução (baixa `yolov8n.pt`, ~6 MB, e o vídeo de exemplo).

## Instalação

```powershell
cd <pasta do projeto>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Não é preciso "ativar" o ambiente. Todos os comandos abaixo usam `.\rodar.cmd`, um atalho de 1 linha que chama `.venv\Scripts\python.exe`. (O `Activate.ps1` costuma ser bloqueado pela política de execução do Windows; `.cmd` não passa por essa política.)

## Rodar

```powershell
# 1. baixar um vídeo de exemplo (pessoas andando)
.\rodar.cmd scripts\baixar_video_exemplo.py

# 2. contar pessoas cruzando uma linha horizontal no meio do frame (abre janela)
.\rodar.cmd scripts\contar.py --fonte data\videos\people-walking.mp4 --classes person --pular 2

# 3. ver o que ficou no banco
.\rodar.cmd scripts\ver_eventos.py
```

Nos exemplos do restante deste documento, leia `python scripts/x.py` como `.\rodar.cmd scripts\x.py`.

Abre uma janela com: caixas coloridas (detecção), `#id` em cada caixa (tracking), rastro do movimento, a linha virtual e os contadores `in` / `out`. No terminal, cada cruzamento imprime uma linha e vira um registro em `data/db/eventos.sqlite`. Tecla `q` fecha.

## Experimentos que valem fazer nesta fase

Cada um ensina algo que vai importar na mesa da tenda:

| Experimento | Comando | O que observar |
|---|---|---|
| Linha vertical | `--linha 0.5,0,0.5,1` | O sentido `in`/`out` depende da direção do segmento (x1,y1→x2,y2). Inverta as pontas e veja trocar. |
| Confiança baixa | `--conf 0.15` | Mais detecções, mais falsos positivos, ids "piscando". |
| Confiança alta | `--conf 0.7` | Perde objetos parcialmente ocultos → tracker perde o id → pode contar 2× ou 0×. |
| Outras classes | `--classes car truck` no vídeo `vehicles` | Como o filtro de classe limpa a cena. |
| Webcam | `--fonte 0` | Passe uma garrafa (`bottle`) ou celular (`cell phone`) pela frente da câmera cruzando a linha. **Isso já simula a mesa.** |
| Snapshots | `--snapshots` | Cada evento salva o frame **anotado** (caixas, ids, linha) em `data/snapshots/<sessao>/`. É a evidência de auditoria: abre a imagem e vê qual objeto cruzou. |
| Vídeo anotado | `--saida-video data/saida/teste.mp4 --sem-janela` | Como vai rodar num servidor sem tela. |
| Pular frames | `--pular 3` | Processa 1 a cada 3 frames. Contagem quase igual, 3× mais rápido. É o que permite webcam ao vivo em CPU fraca. |
| Vídeo com esteira | `baixar_video_exemplo.py milk-bottling-plant` + `--classes bottle` | Objetos iguais passando em fila num fundo controlado — o mais parecido com a bancada da tenda. |
| **Modo zonas** | `--zonas data\zonas\exemplo_people_walking.json` | É o modo da tenda. Eventos viram transições (`fora->centro`), e o rodapé mostra quantos objetos há em cada zona agora. |
| Desenhar zonas | `definir_zonas.py --fonte data\videos\people-walking.mp4 --nomes a b --saida data\zonas\meu.json` | Clique os cantos, `ENTER` fecha a zona, `S` salva. Depois rode `contar.py --zonas data\zonas\meu.json`. |
| Regras sem vídeo | `testar_zonas.py` | Teste sintético: vai-e-volta anulado, entrega direta contada. Roda em 1 s, sem modelo. |

## O que está no código

- [`src/cestas/pipeline.py`](../src/cestas/pipeline.py) — classe `Contador`. Um frame entra, YOLO detecta, `ByteTrackTracker` (pacote `trackers`) dá identidade, `LineZone` verifica se o **centro** da caixa cruzou a linha (só o centro, para uma mão encostando na linha não contar), e cada cruzamento vira `EventStore.registrar(...)`.
  - Objetos que o tracker ainda não confirmou (vistos há menos de 2 frames) vêm com `tracker_id = -1` e são **descartados antes da linha**. Sem isso, todos os "-1" viram um único objeto fantasma e a contagem explode (foi o primeiro bug encontrado no teste zero: 112 `in` num vídeo com ~10).
- [`src/cestas/zonas.py`](../src/cestas/zonas.py) — modo zonas: polígonos nomeados + máquina de estados por objeto. Uma transição só é aceita depois de `--confirmacao` frames seguidos na zona nova (evita tremor na fronteira).
- [`src/cestas/db.py`](../src/cestas/db.py) — tabela `eventos`: hora, câmera, sessão, track_id, classe, direção (`in`/`out` ou `a->b`), frame, segundo do vídeo, confiança, snapshot, `anulado`. A regra de vai-e-volta (`a->b` seguido de `b->a` em ≤ N s) vive aqui, em `registrar_transicao`.
- [`scripts/contar.py`](../scripts/contar.py) — só argumentos de linha de comando; não tem lógica.

Trocar o modelo COCO pelo modelo treinado com cestas (Fase 2) é **um argumento**: `--modelo runs/.../best.pt --classes cesta`. Nada mais muda.

## Critério de conclusão

- [ ] Vídeo de exemplo roda com janela e contadores.
- [ ] `ver_eventos.py` mostra a sessão com `in`/`out` coerentes com o que se viu na tela.
- [ ] Webcam do notebook conta um objeto passando pela linha (ida = `in`, volta = `out`).
- [ ] Zonas desenhadas na webcam (`definir_zonas.py --fonte 0`) e um objeto gerando `a->b` ao ser movido de uma zona para outra.
- [ ] Entendido por que `--conf` muito alto **e** muito baixo pioram a contagem.

## Resultado do primeiro teste (14/09/2026)

`people-walking.mp4` (1920×1080, 25 fps, 341 frames), linha horizontal no meio, `--classes person`:

```
cruzamentos  in: 11   out: 13
```

Coerente com o vídeo (praça com pessoas cruzando nos dois sentidos). Observações que já valem para a mesa:

- **Vai-e-volta**: `#44` cruzou `in` no frame 252, `out` no 257, `in` de novo no 261. Uma pessoa hesitou em cima da linha. Na tenda isso é "cesta ajeitada" — o modo zonas já anula pares assim (`--vai-e-volta`, padrão 4 s); confirmado no teste sintético `testar_zonas.py`.
- **Modo zonas** no mesmo vídeo (`exemplo_people_walking.json`, faixas `esquerda`/`centro`): 6 transições em 341 frames, snapshots mostram as zonas coloridas e o objeto que mudou.
- **Desempenho nesta máquina**: ~270 ms por frame (CPU com 2 threads) ≈ 3,7 fps a 1080p. Com `--pular 3` fica utilizável ao vivo. Num i5 comum espera-se 10–20 fps.
- Confiança dos eventos variou de 0,37 a 0,83 — um filtro por confiança mínima no *evento* (não só na detecção) pode reduzir falsos positivos.

## Problemas conhecidos / dicas

- **Primeira execução lenta**: baixa os pesos do YOLO (`yolov8n.pt`, 6 MB). Depois é instantâneo.
- **Janela não abre / erro de `cv2.imshow`**: use `--sem-janela --saida-video ...` e assista o mp4.
- **FPS baixo**: use `--pular 2` ou `3`. Na mesa não importa (cesta demora segundos para cruzar a linha).
- **Mesmo objeto contado duas vezes**: o tracker perdeu o id no meio (oclusão). Na mesa real a solução é posição de câmera + iluminação, não código.
- **`sv.ByteTrack` deprecado**: o supervision 0.28+ moveu o tracker para o pacote `trackers` (`ByteTrackTracker`, método `update()`). Já está assim no código.
