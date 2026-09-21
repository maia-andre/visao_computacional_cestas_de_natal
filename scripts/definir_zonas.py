"""Desenha as zonas clicando sobre um frame do vídeo e salva em JSON.

    .\\rodar.cmd scripts\\definir_zonas.py --fonte data\\videos\\ensaio_tenda_01.mp4 ^
        --nomes paletes bancada --saida data\\zonas\\tenda.json

Uso na janela:
    clique esquerdo   adiciona um ponto ao polígono atual
    ENTER             fecha o polígono atual e passa para a próxima zona
    U                 desfaz o último ponto
    R                 recomeça a zona atual
    S                 salva e sai (só depois de fechar todas as zonas)
    Q / ESC           sai sem salvar

As coordenadas são salvas em fração do frame (0–1), então o mesmo JSON serve
para qualquer resolução da mesma câmera/enquadramento. O que ficar fora de
todas as zonas é a zona implícita `fora` (funcionário indo embora, por ex.).

Dica: a zona `bancada` pode ter o formato de "L" — é só clicar os 6 cantos.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

CORES = [(28, 159, 255), (182, 196, 46), (54, 29, 231), (236, 56, 131), (255, 134, 58)]  # BGR


def pegar_frame(fonte: str | int, indice: int) -> np.ndarray:
    cap = cv2.VideoCapture(fonte)
    if not cap.isOpened():
        raise SystemExit(f"não consegui abrir: {fonte!r}")
    if indice > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, indice)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("não consegui ler um frame")
    return frame


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fonte", required=True, help="vídeo, índice da webcam ou URL rtsp")
    p.add_argument("--frame", type=int, default=0, help="qual frame usar como fundo (padrão: 0)")
    p.add_argument("--nomes", nargs="+", required=True, help="nomes das zonas, na ordem em que serão desenhadas")
    p.add_argument("--saida", required=True, help="caminho do JSON de saída")
    p.add_argument("--escala", type=float, default=0.0,
                   help="fator de exibição (ex.: 0.5 para caber na tela). 0 = automático")
    args = p.parse_args()

    fonte: str | int = int(args.fonte) if args.fonte.isdigit() else args.fonte
    frame = pegar_frame(fonte, args.frame)
    H, W = frame.shape[:2]
    escala = args.escala or min(1.0, 1280 / W, 720 / H)
    base = cv2.resize(frame, None, fx=escala, fy=escala) if escala != 1.0 else frame.copy()

    zonas: list[list[tuple[int, int]]] = []   # fechadas (em pixels da imagem exibida)
    atual: list[tuple[int, int]] = []
    janela = "definir zonas — ENTER fecha zona, S salva, Q sai"

    def desenhar() -> np.ndarray:
        img = base.copy()
        for i, pts in enumerate(zonas):
            cor = CORES[i % len(CORES)]
            cv2.polylines(img, [np.array(pts, np.int32)], True, cor, 2)
            cx, cy = np.mean(pts, axis=0).astype(int)
            cv2.putText(img, args.nomes[i], (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2)
        i = len(zonas)
        if i < len(args.nomes):
            cor = CORES[i % len(CORES)]
            for pt in atual:
                cv2.circle(img, pt, 5, cor, -1)
            if len(atual) > 1:
                cv2.polylines(img, [np.array(atual, np.int32)], False, cor, 2)
            texto = f"desenhando: {args.nomes[i]}  ({len(atual)} pontos)"
        else:
            texto = "todas as zonas fechadas — S para salvar"
        cv2.putText(img, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 3)
        cv2.putText(img, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
        return img

    def clique(evento, x, y, _flags, _param):
        if evento == cv2.EVENT_LBUTTONDOWN and len(zonas) < len(args.nomes):
            atual.append((x, y))

    cv2.namedWindow(janela)
    cv2.setMouseCallback(janela, clique)

    while True:
        cv2.imshow(janela, desenhar())
        k = cv2.waitKey(30) & 0xFF
        if k in (ord("q"), 27):
            print("saiu sem salvar")
            break
        if k == ord("u") and atual:
            atual.pop()
        elif k == ord("r"):
            atual.clear()
        elif k == 13:  # ENTER
            if len(atual) >= 3:
                zonas.append(list(atual))
                atual.clear()
            else:
                print("uma zona precisa de pelo menos 3 pontos")
        elif k == ord("s"):
            if len(zonas) < len(args.nomes):
                print(f"faltam zonas: {args.nomes[len(zonas):]}")
                continue
            saida = Path(args.saida)
            saida.parent.mkdir(parents=True, exist_ok=True)
            dados = {
                "fonte": str(args.fonte),
                "resolucao": [W, H],
                "zonas": [
                    {"nome": nome, "pontos": [[round(x / escala / W, 4), round(y / escala / H, 4)] for x, y in pts]}
                    for nome, pts in zip(args.nomes, zonas)
                ],
            }
            saida.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"salvo: {saida}")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
