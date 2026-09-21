# Fase 3 — Câmera da tenda (zonas)

**Objetivo:** contagem por transição de zona com erro ≤ 5% versus contagem manual, nos vídeos da tenda (ensaio e/ou operação). **Só depois disso** se compra e instala a câmera.

É o MVP inteiro num ponto: uma câmera, três zonas, um banco de eventos.

## Passos

### 1. Desenhar as zonas sobre um frame do vídeo

```powershell
.\rodar.cmd scripts\definir_zonas.py --fonte data\videos\ensaio_tenda_01.mp4 --nomes paletes bancada --saida data\zonas\tenda.json
```

Clique os cantos de cada polígono (a bancada em L tem 6 cantos), `ENTER` fecha a zona, `S` salva. O que sobrar é `fora`.

Regras para desenhar:
- **`paletes`**: cobre os paletes dentro do L e o chão onde o operador circula com a cesta na mão. Não precisa ser justa.
- **`bancada`**: a superfície da bancada, com uma pequena margem para fora (a cesta "apoiada na beirada" ainda é bancada).
- Entre `paletes` e `bancada` **não deixe corredor de `fora`** — senão uma cesta passando gera `paletes->fora->bancada` (2 eventos em vez de 1). As zonas devem se tocar.
- **`fora`** é onde o funcionário se afasta com a cesta — e onde fica o carro, se ele aparecer no quadro.

O JSON guarda frações (0–1), então serve para qualquer resolução do mesmo enquadramento. Se a câmera mudar de lugar, redesenhe.

### 2. Rodar

```powershell
.\rodar.cmd scripts\contar.py --fonte data\videos\ensaio_tenda_01.mp4 ^
    --modelo runs\cestas_v1\weights\best.pt --classes cesta ^
    --zonas data\zonas\tenda.json --camera tenda --sessao ensaio_01 --snapshots
```

Saída típica:

```
[frame    412    16.5s] cesta #7   paletes->bancada
[frame    598    23.9s] cesta #7   bancada->fora
[frame    640    25.6s] cesta #12  paletes->bancada
[frame    655    26.2s] cesta #12  bancada->paletes  (vai-e-volta: anulado)
...
transições (sem vai-e-volta):
  bancada->fora            37
  paletes->bancada         41
  paletes->fora             3
objetos em cada zona no último frame: {'paletes': 18, 'bancada': 4}
```

### 3. Comparar com a verdade

| vídeo | processadas real | sistema (`paletes->bancada` + `paletes->fora`) | entregues real | sistema (`bancada->fora` + `paletes->fora`) | erro % |
|---|---|---|---|---|---|
| ensaio_01 | | | | | |
| ensaio_02 (pilhas de 2) | | | | | |
| ensaio_03 (entrega direta) | | | | | |
| operação_pico | | | | | |

Meta: erro ≤ 5% em **todos**, inclusive pico.

### 4. Ajustar — nesta ordem

1. **Zonas.** A maioria dos erros iniciais é desenho: corredor de `fora` entre zonas, bancada estreita demais, paletes cortados.
2. **`--confirmacao`** (padrão 3 frames). Subir se a caixa "treme" na fronteira e gera transições falsas; descer se cestas rápidas passam sem confirmar.
3. **`--vai-e-volta`** (padrão 4 s). Assista os anulados nos snapshots: se estão anulando movimentos reais, diminua; se sobram ajeitadas contadas, aumente.
4. **`--conf`**: varrer 0.25 / 0.35 / 0.5.
5. **`--pular`**: se a máquina não acompanha, pular 2–3 frames costuma não mudar a contagem (a cesta demora segundos para atravessar).
6. **Só por último**: mais dados / modelo maior.

### 5. Classificar os erros pelos snapshots

Cada evento salvou o frame anotado (caixas, ids, zonas). Abrir os das sessões com erro:

| sintoma | causa provável | correção |
|---|---|---|
| 1 cesta gerou 2 `paletes->bancada` | tracker perdeu o id no meio (mão cobriu) e o novo id "nasceu" em paletes | câmera mais alta / luz; zona paletes menor |
| pilha de 2 contou 1 | detector vê uma caixa só | classe `pilha2` (Fase 2) ou câmera mais oblíqua |
| `paletes->fora` sem ser entrega direta | operador passou por `fora` a caminho da bancada | zonas devem se tocar; ampliar `paletes` |
| cesta parada na bancada gerando eventos | fronteira passa em cima de onde ficam apoiadas | mover a fronteira |
| contou sacola / caixa | falso positivo | exemplos negativos no dataset; subir `--conf` |

## Instalação física (só depois da meta batida)

Ver [hardware_cameras.md](hardware_cameras.md). Resumo:

- 1 câmera (webcam USB se o PC fica ao lado; IP/RTSP se longe), fixada na estrutura da tenda.
- Enquadramento: **paletes de um lado, bancada no meio, lado do funcionário do outro** — as três zonas em faixas, o menos sobrepostas possível.
- Ângulo: começar **oblíquo alto (~50–60° em relação ao chão)** de fora do L olhando para dentro — mostra pilhas de 2 e ainda separa cestas. Se a oclusão entre cestas na bancada for problema, subir para top-down.
- **Luminária LED** sobre a bancada. Sem contraluz da entrada da tenda.
- Redesenhar as zonas com `definir_zonas.py` usando a câmera instalada (`--fonte 0` ou RTSP).

```powershell
.\rodar.cmd scripts\contar.py --fonte 0 --modelo runs\cestas_v1\weights\best.pt --classes cesta --zonas data\zonas\tenda_instalada.json --camera tenda --sessao 2026-12-01_manha --snapshots
```

### Validação em produção (primeiro dia)

Uma pessoa contando manualmente em paralelo, 1 hora. Mesma tabela. ≥ 95% → o sistema entra como **segunda conferência** (a manual continua até a Fase 4 fechar).

## Critério de conclusão

- [ ] Zonas desenhadas e versionadas (`data/zonas/tenda.json` + foto do enquadramento em `docs/img/`).
- [ ] Erro ≤ 5% em todos os vídeos, inclusive pilhas, entrega direta e pico.
- [ ] Tabela de tipos de erro preenchida.
- [ ] Câmera e luz instaladas; 1 h real ≥ 95%.
- [ ] Parâmetros finais registrados abaixo.

## Registro da instalação

_(preencher)_

- Câmera / posição / altura / ângulo: ___
- `--zonas`: ___  `--conf`: ___  `--confirmacao`: ___  `--vai-e-volta`: ___  `--pular`: ___
- Foto: `docs/img/tenda_enquadramento.jpg`
