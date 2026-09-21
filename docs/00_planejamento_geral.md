# Planejamento geral — Visão Computacional Cestas de Natal

Este documento é o índice do projeto. O plano conceitual original está em
[`../Plano_Visao_Computacional_Cestas_de_Natal.md`](../Plano_Visao_Computacional_Cestas_de_Natal.md);
aqui está o **plano de execução**, fase a fase, com o que se sabe da operação real.

> Revisado em 14/09/2026: o foco do MVP passou a ser **a tenda** (palete → bancada → pessoa),
> com uma câmera e **zonas** em vez de três câmeras e linhas. Motivos abaixo.

## Princípio

> **Primeiro fazer a câmera contar. Depois fazer a câmera entender. Por último fazer a câmera medir.**

O sucesso não é "ter IA". É responder, com evidência:
**quantas cestas saíram dos paletes, quantas foram entregues e onde está qualquer diferença?**

## A operação, como ela é

```
GALPÃO                                  TENDA
──────────────                          ─────────────────────────────────────────────────────
palete filmado ──► retira filme ──►  palete entra na tenda
(entrada,                                    │
 ~400/ano)                                   │  operadores (dentro do "L") tiram
                                             │  cesta do palete e põem na bancada
                                             ▼
                                     ┌──────────────┐
                                     │   BANCADA    │  em "L"; 4–5 paletes dentro do L,
                                     │   em  L      │  mais paletes na fila fora da tenda
                                     └──────┬───────┘
                                            │  funcionário entrega o VALE-CESTA
                                            │  e retira a cesta da bancada
                                            ▼
                                        funcionário sai
                                        (às vezes 2 cestas empilhadas)

           atalho: funcionário com N vales encosta o carro do lado da tenda,
                   operador leva N cestas do palete direto para a mala.
```

| Fato | Consequência técnica |
|---|---|
| ~16.000 cestas / ~400 paletes por ano (2025) | Volume médio; não exige GPU no MVP |
| Palete **fixo: 5 camadas × 8 = 40** | "Palete esvaziado" deve gerar 40 saídas; divergência por palete é detectável |
| Filme plástico só até a entrada da tenda | Dentro da tenda as cestas estão visíveis individualmente — é onde a câmera funciona |
| Bancada em **"L"**, operadores dentro, paletes dentro | Linha reta não serve; **zonas poligonais** (qualquer formato) |
| **Vai-e-volta** acontece (cesta ajeitada, devolvida) | Transição inversa em poucos segundos anula a anterior — já implementado |
| Funcionário leva **2 empilhadas** | De cima, pilha parece 1 → subcontagem. Câmera oblíqua ou classe `pilha` (decidir com fotos) |
| **Entrega direta** palete → carro (N vales) | Transição `paletes->fora` sem passar pela bancada: contada como entrega, marcada como direta. Se ocorrer fora do quadro, registro manual |
| **Vale-cesta** físico por cesta entregue | Contador independente, sem câmera: vales recolhidos = entregas esperadas |

## Modelo: zonas, não linhas

A câmera da tenda vê **três regiões** e a pergunta do sistema é sempre *"em que zona está cada cesta?"*.
Um evento é uma **transição** de zona:

```
   ┌───────────────────────────────────────────────────────────┐
   │  zona PALETES            zona BANCADA (em L)     (fora)   │
   │  ┌──────────┐            ┌──────────────┐                 │
   │  │ ▓▓ ▓▓ ▓▓ │  ──────►   │ █ █ █ █ █    │  ──────►  🚶     │
   │  │ ▓▓ ▓▓    │ paletes->  │ █ █          │ bancada->        │
   │  │ operador │  bancada   │ █ █          │   fora           │
   │  └──────────┘            └──────────────┘                 │
   │        └───────────── paletes->fora ──────────────►  🚗   │
   │                        (entrega direta)                   │
   └───────────────────────────────────────────────────────────┘
```

| transição | significado | contador |
|---|---|---|
| `paletes->bancada` | operador abasteceu | **processadas** |
| `bancada->fora` | funcionário levou | **entregues** |
| `paletes->fora` | entrega direta (carro) | **entregues** (marcada como direta) |
| `bancada->paletes`, `fora->bancada` | devolução / correção | descontam; se em < 4 s, anulam a anterior (vai-e-volta) |

Cinco números que precisam bater, e cada um é independente dos outros:

```
processadas (paletes->bancada + paletes->fora)   ≈  paletes esvaziados × 40
entregues   (bancada->fora   + paletes->fora)    ≈  vales recolhidos
saldo       (processadas − entregues)            ≈  cestas visíveis na bancada AGORA
```

A última é a **auto-conferência em tempo real**: se o sistema contou 12 na bancada e vê 9, algo foi perdido — e ele sabe *na hora*, com snapshot.

## Pipeline técnico

```
FRAME
  │
  ▼
1. DETECÇÃO ─────── YOLO fine-tunado: "onde estão as cestas (e paletes)?"
  │
  ▼
2. TRACKING ─────── ByteTrack: "a cesta #17 é a mesma do frame anterior"
  │
  ▼
3. ZONAS ────────── centro da caixa está em paletes / bancada / fora?
  │                 mudou e ficou ≥ 3 frames → transição
  ▼
4. REGRAS ───────── vai-e-volta anula; entrega direta marca; palete × 40
  │
  ▼
5. SQLite ───────── evento, hora, track_id, transição, snapshot anotado
```

Modo *linha* (Fase 0) continua existindo para o teste zero; a tenda usa *zonas*.

## Fases

| Fase | Nome | Entregável | Precisa de | Doc |
|---|---|---|---|---|
| 0 | Teste zero | Pipeline rodando num vídeo qualquer (linha e zonas), eventos no SQLite | Só o notebook | [01_fase0_teste_zero.md](01_fase0_teste_zero.md) — **feito 14/09** |
| 1 | Ensaio + gravação | Vídeos da tenda (ensaio controlado e/ou operação real) com contagem manual | Celular + tripé + cestas + 3–4 pessoas | [02_fase1_gravacao.md](02_fase1_gravacao.md) |
| 2 | Ensinar o modelo | YOLO fine-tunado (`cesta`, `palete`, talvez `pilha`), mAP50 ≥ 0,85 | ~300 frames anotados | [03_fase2_modelo.md](03_fase2_modelo.md) |
| 3 | **Câmera da tenda** | Zonas + transições com erro ≤ 5% vs. manual → aí instala câmera | Modelo da Fase 2 | [04_fase3_camera_tenda.md](04_fase3_camera_tenda.md) |
| 4 | Reconciliação | Palete × 40, vale-cesta, entrega direta, divergências com endereço | Fase 3 rodando | [05_fase4_reconciliacao.md](05_fase4_reconciliacao.md) |
| 5 | Dashboard | Streamlit: processadas / entregues / saldo / divergências | Fases 3–4 | [06_fase5_dashboard.md](06_fase5_dashboard.md) |
| + | Galpão (opcional) | Palete completo na entrada (5 camadas × 8), QR Code | Só se a tenda mostrar perda antes dela | [05_fase4_reconciliacao.md](05_fase4_reconciliacao.md#galpão-opcional) |
| — | Hardware | O que comprar, quando, o que evitar | — | [hardware_cameras.md](hardware_cameras.md) |

**Regra de passagem de fase:** cada fase tem um critério numérico. Não se compra câmera antes da Fase 3 bater a meta num vídeo.

## Estrutura do repositório

```
├── Plano_Visao_Computacional_Cestas_de_Natal.md   # plano conceitual original
├── docs/                                          # este planejamento, por fase
├── rodar.cmd                                      # atalho: .\rodar.cmd scripts\x.py (sem ativar venv)
├── src/cestas/
│   ├── pipeline.py                                #   detecção → tracking → linha|zonas → evento
│   ├── zonas.py                                   #   polígonos + máquina de estados por objeto
│   └── db.py                                      #   SQLite de eventos, regra de vai-e-volta
├── scripts/
│   ├── contar.py                                  #   roda o pipeline (vídeo / webcam / RTSP)
│   ├── definir_zonas.py                           #   desenha as zonas clicando num frame → JSON
│   ├── testar_zonas.py                            #   teste sintético (vai-e-volta, entrega direta)
│   ├── baixar_video_exemplo.py
│   └── ver_eventos.py                             #   consulta o banco
├── data/                                          # (não versionar) vídeos, zonas, banco, snapshots
└── requirements.txt
```

## Decisões em aberto (as fotos da operação vão responder)

- **Uma câmera cobre o L inteiro?** Depende do tamanho do L e da altura disponível. Se não, duas câmeras com zonas complementares (uma por braço do L), ou uma só cobrindo o lado por onde o funcionário retira.
- **Top-down ou oblíqua?** Top-down elimina oclusão entre cestas, mas esconde pilhas de 2. Oblíqua (~45–60°) mostra a pilha, mas cestas de trás ficam parcialmente cobertas. Candidato: oblíqua alta, do lado de fora do L, olhando para dentro.
- **Pilha de 2**: classe própria (`pilha2`) ou regra geométrica (caixa 1,6–2× mais alta que a média)? Decidir na Fase 2 com dados reais.
- **Entrega direta fora do quadro**: se o carro fica onde a câmera não vê, o operador registra "entrega em lote: N" no painel (com N vales). O sistema confere `paletes->fora` quando vê; o resto é declarado.
- **Vale-cesta com código?** Se tiver barras/QR, um leitor de R$ 100 na bancada amarra cada entrega a um funcionário — sem reconhecimento facial.

## Privacidade

Câmera apontada para bancada e paletes, não para rostos. Sem reconhecimento facial. A identidade de quem retirou, quando necessária, vem do vale-cesta, não da imagem. Snapshots de evento guardam o frame para auditoria; definir política de retenção antes de entrar em produção.
