# Teste de contagem com filmagem real — 22/09/2026

Primeiro teste ponta a ponta do pipeline sobre vídeo da operação, **antes** do modelo treinado. Objetivo: descobrir o que quebra quando a entrada deixa de ser vídeo de exemplo. Não é a Fase 3.

**Entrada:** `2026-09-21_almox_obliqua_01.mp4` — 63 s, 2160×3840, 30 fps, celular na mão, oblíqua alta do mezanino.
**Gabarito** (`data/videos/verdade.csv`): 10 cestas processadas, 10 entregues, início com 3 no chão + 7 na bancada, fim com tudo vazio.
**Detector:** YOLO-World `yolov8s-worldv2.pt` com o prompt `box`. Não há `best.pt` ainda.
**Zona:** `data/zonas/almox_obliqua_teste.json`, uma única `bancada`.

## Resultado

| medida | câmera | gabarito | |
|---|---|---|---|
| pico de cestas na bancada | 7 | 7 | ✅ |
| cestas na bancada no fim | 0 | 0 | ✅ |
| reposição vinda do chão (≈45 s) | sobe para 4 | 3 vieram do chão | ✅ plausível |
| **entregas contadas** (`bancada->fora`) | **0** | **10** | ❌ |

A curva de ocupação bate. A contagem por transição não produziu nada.

## Por que as entregas deram zero

Rastreando o histórico de zona de cada track: **os 16 tracks nasceram e morreram dentro da `bancada`**, nenhum chegou a `fora`. Quando o funcionário pega a cesta e a encosta no corpo, o detector genérico a perde — o track expira dentro da zona e a saída nunca vira transição.

Não é ajuste de parâmetro. São duas correções já planejadas:

- **Fase 2** — modelo treinado em `cesta` não perde o objeto na mão como o zero-shot perde.
- **Fase 3** — câmera fixa. Aqui o celular estava na mão e derivou até 10% da largura do quadro (medido por correlação de fase entre o primeiro frame e os demais).

A curva de ocupação sobrevive a isso porque só pergunta "quantas cestas há na bancada agora", quadro a quadro, sem precisar de identidade. Por isso um número fecha e o outro não.

## Dois defeitos encontrados no código

### 1. O tracker quase não criava tracks

`pipeline.py` fixava `high_conf_det_threshold=max(confianca, 0.5)`. Esse limiar decide se uma detecção pode **iniciar** um track no ByteTrack; as mais fracas só mantêm os existentes. A confiança do detector zero-shot em cesta fica entre 0,26 e 0,64 — só 1 a 4 das 6 a 9 detecções por frame chegavam a 0,5.

Na primeira rodada isso deu **0 transições e 0 objetos em zona**, um resultado que parecia "o pipeline não funciona" e era configuração. Agora exposto como `--track-conf` (padrão inalterado).

### 2. `contagem_atual()` devolvia valor velho

`MonitorZonas.contagem_atual()` lia `PolygonZone.current_count`. Num frame **sem nenhuma detecção** esse atributo não é zerado: ele retém o valor do frame anterior. Como 15 dos 125 frames do vídeo não têm detecção nenhuma, a bancada continuava marcando "1 cesta" depois de esvaziada — e o fim do vídeo reportava 1 em vez de 0.

Isso contamina o **número C** da conferência ("saldo na bancada"), que é justamente o que se compara com as cestas visíveis. Corrigido em `zonas.py`: a ocupação passa a ser contada a partir da classificação do próprio frame.

## Outras mudanças que o teste exigiu

| flag nova | por quê |
|---|---|
| `--prompt` | o pipeline não sabia passar classes por texto ao YOLO-World |
| `--imgsz` | rodava fixo em 640 px; num quadro 2160×3840 a cesta vira ~15 px. Medido: 1280 dá a mesma detecção que 1920 (4,8 vs 5,0 cestas/frame) pela metade do tempo |
| `--largura-max` | mesmo falso positivo do balcão da pré-anotação |
| `--track-conf`, `--track-buffer` | ver defeito 1 |

## Sobre o custo, e o atalho

Rodar o detector no vídeo inteiro custa ~4 s/frame nesta CPU (~25 min por vídeo). Duas rodadas foram perdidas — uma pelo defeito 1, outra interrompida por falta de memória.

Daí o `scripts/testar_zonas_preanot.py`: ele reaproveita as detecções que o `preanotar.py` já calculou e passa só o tracking e as zonas, em segundos. Serve para ajustar zona e parâmetros antes de gastar uma rodada completa. Limite: os frames pré-anotados são 2 fps contra os 6 fps da leitura direta, então o resultado é um piso.

**Os números desta página vieram do atalho (2 fps).** Uma rodada completa com `contar.py` a 6 fps ainda não foi feita.

## Como reproduzir

```powershell
.\rodar.cmd scripts\testar_zonas_preanot.py --video 01
```

Rodada completa, quando houver CPU e memória sobrando:

```powershell
.\rodar.cmd scripts\contar.py --fonte data\videos\2026-09-21_almox_obliqua_01.mp4 ^
    --modelo yolov8s-worldv2.pt --prompt box --imgsz 1280 --largura-max 50 ^
    --conf 0.25 --track-conf 0.35 --track-buffer 1.5 ^
    --zonas data\zonas\almox_obliqua_teste.json --pular 5 --sem-janela
```

## O que isto muda no plano

Nada de prazo. Confirma a Fase 2 como caminho crítico: sem modelo treinado, a cesta na mão não é detectável de forma estável, e é justamente a cesta na mão que define a entrega. A curva de ocupação, porém, já funciona hoje — é o primeiro número real que o projeto produz.

O resultado está publicado em `docs/vitrine/index.html`, seção "A primeira vez que o código olhou a operação", com o 0/10 declarado junto dos acertos.
