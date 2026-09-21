# Fase 4 — Reconciliação: palete × 40, vale-cesta, entrega direta

**Objetivo:** transformar eventos em **conferência com endereço**: cada divergência aponta para um palete, um período e snapshots.

A Fase 3 entrega contadores. Esta fase cruza os contadores com o que a operação já sabe (padrão de palete, vales) e trata os casos que a câmera não vê inteiros.

## Os cinco números

```
A. processadas  = paletes->bancada  +  paletes->fora        (câmera)
B. entregues    = bancada->fora     +  paletes->fora        (câmera)
C. saldo        = A − B                                     (câmera, derivado)
D. esperado     = paletes esvaziados × 40                   (operação)
E. vales        = vales recolhidos                          (operação, papel)

Conferências:  A ≈ D      B ≈ E      C ≈ cestas visíveis na bancada agora
```

Cada `≈` que falha vira uma **divergência** registrada com tipo, período, e os snapshots dos eventos envolvidos.

## Palete × 40

O padrão fixo (5 × 8) permite conferir palete a palete, sem câmera no galpão:

```
palete entra no quadro (classe `palete` detectada em zona paletes)
        │
        ▼
começa "período do palete"  ─────►  conta paletes->bancada + paletes->fora
        │
        ▼
palete some do quadro / próximo palete entra
        │
        ▼
esperado 40  ×  contado N   →   N = 40 OK  |  N ≠ 40 DIVERGÊNCIA (snapshots do período)
```

Complicação real: **4–5 paletes ficam dentro do L ao mesmo tempo**, e o operador pode tirar de qualquer um. Duas formas de lidar, por ordem de simplicidade:

1. **Sem identificar o palete**: conferir em blocos — "entre 09:00 e 10:30 saíram 3 paletes do quadro → esperado 120 → contado 118". Menos preciso, zero infraestrutura.
2. **QR Code no palete** (colado no galpão, antes do filme): `cv2.QRCodeDetector` lê quando o palete entra na tenda. Cada `paletes->bancada` é atribuído ao palete mais próximo da cesta no frame anterior à transição (posição do centro da caixa vs. posição do palete). Rastreabilidade individual: `PALLET-00037: entrou 09:14, 40 saídas, esvaziado 10:28`.

Começar pela 1; passar para a 2 se as divergências precisarem de mais precisão.

## Vale-cesta

É o contador que **não depende de nenhuma câmera**. No fechamento do dia (ou por turno):

| | |
|---|---|
| vales recolhidos | 1.238 |
| `bancada->fora` + `paletes->fora` | 1.231 |
| diferença | 7 → investigar: entregas diretas fora do quadro? pilhas de 2 contadas como 1? |

Se o vale tiver **código de barras / QR**: leitor USB (R$ 100–200) na bancada, o operador bipa ao receber. O bipe vira um evento `vale` com hora; o sistema pareia cada `bancada->fora` com o `vale` mais próximo no tempo. Resultado: entrega individual sem reconhecimento facial. Se o vale for papel simples, o total já basta.

## Entrega direta (palete → carro)

Três situações:

| situação | o que a câmera vê | tratamento |
|---|---|---|
| Carro dentro do quadro | `paletes->fora` para cada cesta | Contada como entregue, marcada `direta`. Nada a fazer. |
| Carro fora do quadro, cestas saem pelo quadro | `paletes->fora` | Idem. |
| Cestas tiradas de palete **fora da tenda** (fila) | nada | **Registro manual**: operador lança "entrega em lote: N cestas, N vales, hora" no painel. Entra em B e em E. |

A regra é: a câmera conta o que vê; o que ela não vê é **declarado**, e o vale fecha a conta.

## Pilha de 2

Fase 2 decide o mecanismo (classe `pilha2` ou regra de altura). Aqui, a reconciliação usa a pilha assim: `bancada->fora` de uma `pilha2` = +2 entregues. Se o modelo não distinguir, o desvio aparece na conferência B ≈ E (câmera conta menos que os vales) — e o tamanho do desvio diz quanto vale investir no problema.

## Código desta fase

`src/cestas/reconciliacao.py`:
- `totais(sessao | período)` → A, B, C;
- `periodos_de_palete(sessao)` → lista de janelas com contagem e status (× 40);
- `divergencias(...)` → registros com tipo, referência, ids de eventos, snapshots;
- tabela `lancamentos_manuais` (entrega em lote, vales recolhidos) e `divergencias` no SQLite.

O dashboard (Fase 5) só exibe o que esta camada calcula.

## Critério de conclusão

- [ ] A, B, C calculados por sessão e por período.
- [ ] Conferência palete × 40 por bloco funcionando; divergência aponta snapshots.
- [ ] Lançamento manual de entrega em lote e de vales recolhidos.
- [ ] Um dia de operação (ou ensaio completo) reconciliado ponta a ponta: A ≈ D, B ≈ E, com todas as diferenças explicadas.

---

## Galpão (opcional)

Só entra se a reconciliação da tenda mostrar perda **antes** da tenda (A consistentemente < D e as divergências não se explicam dentro dela).

**O que a câmera do galpão faria:** verificar se o palete que chega está completo, por geometria — não contar 40 cestas através do filme.

```
palete filmado detectado (vista lateral + oblíqua)
   ├── camadas visíveis: 5?          (linhas horizontais, visíveis pelo filme)
   └── camada do topo: 8 cestas?     (é a que falta quando o palete vem incompleto)
   → estimativa = camadas × 8 + topo ; status OK / DIVERGÊNCIA
```

Abordagens, da mais simples: altura da caixa `palete` em pixels ÷ referência (ArUco na parede) → nº de camadas; ou classes `palete_completo` / `palete_incompleto`. Mais o QR Code colado antes do filme, que já serve à rastreabilidade da tenda.

Hardware: câmera IP RTSP/PoE (ver [hardware_cameras.md](hardware_cameras.md)).
