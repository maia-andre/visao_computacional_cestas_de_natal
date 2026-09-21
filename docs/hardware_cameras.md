# Hardware — câmeras, iluminação, computador

Resumo: **não comprar câmera antes da Fase 3.** Nas fases de gravação e validação, o celular é a melhor câmera disponível.

## Por fase

| Fase | Câmera | Computador |
|---|---|---|
| 0 — Teste zero | Webcam do notebook (opcional) | Notebook comum |
| 1 — Ensaio / gravação | **Celular** 1080p @ 30 fps + tripé | — |
| 2 — Modelo | — | Notebook (1–2 h) ou Google Colab grátis (15 min) |
| 3 — Tenda | **1 câmera**: webcam USB 1080p se o PC fica a ≤ 5 m; câmera IP RTSP/PoE se longe ou se o L exigir 2 câmeras | Notebook/mini-PC na tenda |
| Galpão (opcional) | Câmera IP RTSP + PoE (Intelbras VIP, Hikvision, Dahua, 2 MP) + switch PoE | Mesmo computador ou 1 GPU NVIDIA de entrada |
| Medição (futuro) | Câmera de profundidade (Intel RealSense, Luxonis OAK-D) ou ArUco com câmera calibrada | — |

## A câmera da tenda — o que as fotos precisam responder

- **Onde fixar**: a estrutura da tenda tem ponto a 2,5–3,5 m de altura, do lado de fora do L, com visão para dentro? Se não, um poste/tripé alto (2,5 m) resolve.
- **Uma ou duas câmeras**: um L de até ~3 × 3 m cabe numa câmera oblíqua a 3 m. Maior que isso, ou se os paletes ficam atrás da bancada tapando a visão, uma por braço do L.
- **USB × IP**: USB é mais simples (plug e `--fonte 0`), mas o cabo limita a ~5 m do computador. IP vai a 100 m pelo cabo de rede e alimenta pelo próprio cabo (PoE).

## Celular (Fase 1)

- 1080p, 30 fps. **Não 4K**: arquivo 4× maior, o modelo reduz para 640 px de qualquer jeito.
- Tripé (R$ 40–80). Enquadramento estável e reproduzível.
- Travar exposição e foco (AE/AF lock).
- Bateria e espaço: 15 min de 1080p ≈ 1,5–2 GB.

## Webcam USB (Fase 3 — tenda, se o PC fica perto)

Por quê: plug-and-play, sem rede, sem latência, `--fonte 0`.

- Logitech C920 / C922 / Brio (1080p) ou equivalente. R$ 300–600.
- Cabo USB: até ~5 m sem extensor; além disso, extensor USB ativo.
- Fixação: estrutura da tenda ou poste, **oblíqua alta** (~50–60°) de fora do L, a 2,5–3 m; top-down como alternativa.
- Desligar auto-exposição/auto-foco no driver depois de ajustado (Logitech: app "Logi Tune" ou `cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, ...)`).

## Câmera IP (tenda se longe do PC; galpão)

Por quê: cabo de rede vai até 100 m, alimentação pelo próprio cabo (PoE), OpenCV lê o stream direto.

- Requisito **obrigatório**: expõe stream **RTSP** (a maioria das Intelbras VIP, Hikvision, Dahua expõe). Confirmar na ficha técnica antes de comprar.
- 2 MP (1080p) basta. 4 MP+ só encarece e pesa.
- Lente 2,8–4 mm para ambientes internos; **evitar fisheye/180°**.
- PoE + switch PoE (4–8 portas, R$ 200–400).
- R$ 250–500 por câmera.

```python
cv2.VideoCapture("rtsp://usuario:senha@192.168.0.10:554/cam/realmonitor?channel=1&subtype=0")
```

(URL varia por fabricante; está no manual da câmera.)

## O que evitar

| Item | Motivo |
|---|---|
| Câmera Wi-Fi de consumo (Tuya, Xiaomi, "babá eletrônica") | Latência, compressão pesada, muitas não expõem RTSP ou dependem de app em nuvem |
| Lente fisheye / grande angular | Distorce bordas; atrapalha contagem e inviabiliza medição futura |
| 4K | Custo e processamento maiores, sem ganho |
| Câmera "com IA embarcada que conta objetos" | Você quer o vídeo cru; a inteligência é sua e é auditável |
| Câmera com IR forte apontada para plástico filme | Reflexo cega a imagem à noite |

## Iluminação (mais importante que a câmera)

Uma luminária LED de R$ 80 sobre a bancada vale mais que R$ 1.000 de câmera.

- Luz **uniforme e difusa** sobre a bancada e a fronteira paletes/bancada.
- Sem sombra dura (mãos criam sombras que o modelo confunde com objeto).
- Sem contraluz: a porta da tenda não pode estar "atrás" do que a câmera vê.
- Constante ao longo do dia: se entra sol, a luz artificial precisa dominar.

## Computador

| Cenário | Mínimo | Confortável |
|---|---|---|
| 1 câmera, `yolov8n` | i5/Ryzen 5, 8 GB RAM, sem GPU (~10–20 fps) | 16 GB RAM |
| 3 câmeras simultâneas | 3 máquinas modestas (1 por câmera) | 1 máquina com GPU NVIDIA (GTX 1650 / RTX 3050+), 16 GB RAM |
| Fase 9 — 3D | — | GPU + câmera de profundidade |

Na tenda, uma cesta leva segundos para mudar de zona; 10 fps é folga (e `--pular 2` resolve máquinas fracas). Não comprar GPU antes de ter ≥ 3 câmeras rodando.

## Referências geométricas (Fase 4 e 9)

- **ArUco**: marcador impresso (tipo QR simplificado) de tamanho conhecido colado na parede/chão. OpenCV detecta e devolve a relação pixel ↔ cm naquele plano. Gratuito, robusto, sem IA. É o caminho para "quantas camadas tem o palete" por altura, e depois para medir.
- **QR Code**: identificação (`PALLET-00037`), não medição. `cv2.QRCodeDetector` nativo.
