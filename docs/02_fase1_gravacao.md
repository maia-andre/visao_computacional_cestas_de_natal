# Fase 1 — Ensaio e gravação da tenda

**Objetivo:** vídeos da tenda (palete → bancada → pessoa), no ângulo candidato da câmera definitiva, **com contagem manual anotada** para servir de verdade.

Sem esta fase não existe Fase 2 (não há o que anotar) nem Fase 3 (não há contra o que validar). É a fase mais "chata" e a mais importante.

## Duas formas de fazer — de preferência as duas

### A. Ensaio controlado (pode ser feito antes da operação)

Ambiente estático, 3–4 pessoas, 20–40 cestas (ou caixas de tamanho parecido, se ainda não houver cesta — o modelo é retreinado depois de qualquer jeito).

- Uma bancada montada em **L**, como na operação. Se não der, uma mesa reta serve para o primeiro ensaio; o L entra no segundo.
- 1–2 pessoas de **operador**: tiram do "palete" (pilha de cestas no chão) e põem na bancada.
- 1–2 pessoas de **funcionário**: chegam, "entregam o vale", pegam a cesta e saem do quadro.
- Alguém **contando e anotando**.

Roteiro sugerido (20–30 min no total), cada trecho num vídeo separado:

| vídeo | o que acontece | para testar |
|---|---|---|
| `ensaio_01_normal` | fluxo tranquilo, 1 cesta por vez | baseline |
| `ensaio_02_vai_e_volta` | operador ajeita, devolve, troca cesta de lugar | regra de vai-e-volta |
| `ensaio_03_pilhas` | funcionário leva 2 empilhadas, várias vezes | subcontagem de pilha |
| `ensaio_04_direta` | "carro" (mesa/caixa) do lado; operador leva 5–10 direto do palete | `paletes->fora` |
| `ensaio_05_pico` | todo mundo ao mesmo tempo, mãos, gente na frente | pior caso |

### B. Operação real

Quando houver cestas e paletes de verdade: celular fixo na posição candidata, 10–15 min por trecho, em ≥ 2 horários (luz diferente) e no pico. Aqui aparece o que o ensaio não simula: plástico das cestas refletindo, ritmo real, 4–5 paletes dentro do L.

## Equipamento

- Celular com câmera 1080p @ 30 fps. **Não 4K.**
- Tripé ou suporte fixo (R$ 40–80), ou celular preso na estrutura da tenda. O enquadramento precisa ser estável e reproduzível.
- Planilha + relógio sincronizado com o celular.

## Regras de gravação

1. **Travar exposição e foco** (tocar e segurar na tela → AE/AF lock).
2. **Celular fixo.** Nada de segurar na mão.
3. **Gravar de onde a câmera definitiva ficaria.** Cada vídeo é um teste de posição.
4. **Nomear na hora**: `2026-11-03_tenda_obliqua_01.mp4`. Nunca `VID_20261103.mp4`.
5. **Anotar a verdade junto**: hora de início e, para cada cesta que sai do palete e para cada que sai com funcionário, um risco. No fim: `processadas: 41 / entregues: 37 / diretas: 3`.

## Posições de câmera a testar

| posição | prós | contras |
|---|---|---|
| **Oblíqua alta (~50–60°)**, de fora do L olhando para dentro, paletes ao fundo, bancada no meio, funcionário na frente | mostra pilha de 2; três zonas em faixas | cestas de trás parcialmente cobertas |
| **Top-down** (de cima, 2,5–3 m) | zero oclusão entre cestas na bancada | pilha de 2 parece 1; exige estrutura alta |
| Oblíqua baixa (~30°) | fácil de fixar | muita oclusão por pessoas; evitar |

Gravar pelo menos oblíqua alta e top-down do **mesmo** trecho de ensaio, para comparar na Fase 3.

## Planilha de verdade (modelo)

| arquivo | posição | início | fim | processadas | entregues | diretas | pilhas de 2 | observações |
|---|---|---|---|---|---|---|---|---|
| ensaio_01_normal_obliqua.mp4 | oblíqua alta | 14:02:00 | 14:08:30 | 41 | 37 | 0 | 0 | luz boa |

Salvar como `data/videos/verdade.csv`.

## Fotos (antes de tudo)

Fotos da operação anterior respondem, sem gravar nada:
- tamanho e formato do L; onde ficam os 4–5 paletes; por onde o funcionário chega e sai;
- altura da estrutura da tenda (onde a câmera pode ser fixada);
- de onde vem a luz (abertura da tenda, sol);
- como a cesta se parece (cor, brilho da embalagem, alça).

Com isso se decide o enquadramento antes do ensaio.

## Critério de conclusão

- [ ] Ensaio: os 5 roteiros gravados em ≥ 2 posições, com verdade anotada.
- [ ] Operação real (quando houver): ≥ 30 min, ≥ 2 condições de luz, pico incluído.
- [ ] `verdade.csv` preenchido.
- [ ] Decisão preliminar de posição (oblíqua × top-down) registrada em `docs/00`.

## Privacidade

Os vídeos terão pessoas. São material de desenvolvimento: pasta restrita, sem compartilhar fora do projeto, e ao anotar (Fase 2) marcam-se apenas cestas, pilhas e paletes.
