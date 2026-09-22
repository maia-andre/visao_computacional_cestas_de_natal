"""Extrai frames dos vídeos da Fase 1 para anotação (Fase 2).

    .\\rodar.cmd scripts\\extrair_frames.py data\\videos\\2026-09-21_almox_obliqua_01.mp4 [--cada 0.5] [--altura 1920]

Um frame a cada `--cada` segundos, redimensionado para que o lado maior tenha
`--altura` px (4K do celular vira 1080x1920). Saída em data/dataset/frames/<nome_do_video>/.
Frames consecutivos são quase idênticos; 0,5–1 s entre eles é o suficiente.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "data" / "dataset" / "frames"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--cada", type=float, default=0.5, help="segundos entre frames")
    ap.add_argument("--altura", type=int, default=1920, help="lado maior após redimensionar")
    args = ap.parse_args()

    for video in args.videos:
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        passo = max(1, round(fps * args.cada))
        destino = SAIDA / video.stem
        destino.mkdir(parents=True, exist_ok=True)

        n = 0
        for idx in range(0, total, passo):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            escala = args.altura / max(h, w)
            if escala < 1:
                frame = cv2.resize(frame, (round(w * escala), round(h * escala)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(destino / f"{video.stem}_{idx:06d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            n += 1
        cap.release()
        print(f"{video.name}: {n} frames -> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
