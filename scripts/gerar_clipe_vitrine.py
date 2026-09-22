"""Gera o clipe anotado que a vitrine mostra, a partir da filmagem real.

    .\\rodar.cmd scripts\\gerar_clipe_vitrine.py --inicio 8 --fim 20

Saída: `docs/vitrine/clipe-almoxarifado.webp` (WebP animado — esta máquina não tem
ffmpeg nem OpenH264, então o OpenCV só escreveria MPEG-4 Parte 2, que navegador
não toca; WebP animado roda em `<img>` sem codec nenhum).

Três coisas acontecem por quadro:

1. **Rostos borrados.** O repositório é público e a filmagem mostra servidores.
   Cada pessoa detectada tem o terço superior da caixa (cabeça e ombros) borrado
   em resolução plena, *antes* da redução. A confiança do detector de pessoa é
   deliberadamente baixa (0,20): borrar demais é inofensivo, borrar de menos não.
2. **Cestas detectadas e rastreadas**, com o mesmo YOLO-World e o mesmo ByteTrack
   do pipeline — é o que se quer mostrar.
3. **Recorte** na faixa onde a operação acontece, para não gastar pixel com o
   chão vazio da metade de baixo do quadro retrato.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from PIL import Image
from trackers import ByteTrackTracker
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "vitrine" / "clipe-almoxarifado.webp"

# faixa do quadro onde a operação acontece (fração da altura)
RECORTE_Y = (0.24, 0.72)
CESTA = (120, 235, 90)    # BGR
PESSOA = (210, 150, 60)


def borrar(img: np.ndarray, caixas: list[tuple[int, int, int, int]]) -> None:
    """Borra a cabeça/ombros de cada pessoa, no lugar."""
    h, w = img.shape[:2]
    for x1, y1, x2, y2 in caixas:
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        bw, bh = (x2 - x1) * 1.3, (y2 - y1) * 1.3          # folga: a caixa é justa demais
        a = max(0, int(cx - bw / 2)), max(0, int(cy - bh / 2))
        b = min(w, int(cx + bw / 2)), min(h, int(cy - bh / 2 + bh * 0.45))
        if b[0] <= a[0] or b[1] <= a[1]:
            continue
        r = img[a[1]:b[1], a[0]:b[0]]
        # pixelar e depois borrar: nenhum dos dois sozinho é suficiente
        pequeno = cv2.resize(r, (max(1, r.shape[1] // 22), max(1, r.shape[0] // 22)), interpolation=cv2.INTER_AREA)
        r[:] = cv2.GaussianBlur(cv2.resize(pequeno, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_NEAREST), (0, 0), 9)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, default=RAIZ / "data" / "videos" / "2026-09-21_almox_obliqua_01.mp4")
    ap.add_argument("--inicio", type=float, default=8.0, help="segundo inicial")
    ap.add_argument("--fim", type=float, default=20.0, help="segundo final")
    ap.add_argument("--fps", type=float, default=6.0, help="quadros por segundo do clipe")
    ap.add_argument("--largura", type=int, default=640, help="largura final em px")
    ap.add_argument("--qualidade", type=int, default=58)
    args = ap.parse_args()

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        sys.exit(f"não consegui abrir {args.video}")
    fps_src = cap.get(cv2.CAP_PROP_FPS) or 30.0
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    passo = max(1, round(fps_src / args.fps))
    i0, i1 = int(args.inicio * fps_src), int(args.fim * fps_src)
    y0, y1 = int(RECORTE_Y[0] * H), int(RECORTE_Y[1] * H)

    cestas = YOLO("yolov8s-worldv2.pt"); cestas.set_classes(["box"])
    pessoas = YOLO("yolov8n.pt")
    tracker = ByteTrackTracker(frame_rate=args.fps, track_activation_threshold=0.25,
                               high_conf_det_threshold=0.35,
                               lost_track_buffer=max(1, int(args.fps * 1.5)),
                               minimum_consecutive_frames=2)

    rastros: dict[int, list[tuple[int, int]]] = {}
    quadros: list[Image.Image] = []
    print(f"{args.video.name}  {args.inicio:.0f}s-{args.fim:.0f}s a {args.fps:g} fps")

    for idx in range(i0, i1, passo):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]

        rp = pessoas.predict(frame, conf=0.20, classes=[0], imgsz=640, verbose=False)[0]
        rc = cestas.predict(frame, conf=0.25, imgsz=1280, verbose=False)[0]

        borrar(frame, [tuple(int(v) for v in b.xyxy[0]) for b in rp.boxes])

        caixas, confs = [], []
        for b in rc.boxes:
            x1, y1b, x2, y2b = (float(v) for v in b.xyxy[0])
            if 100 * (x2 - x1) / w > 50:          # balcão, ver docs/03_fase2_modelo.md
                continue
            caixas.append([x1, y1b, x2, y2b]); confs.append(float(b.conf))
        det = sv.Detections(xyxy=np.array(caixas, dtype=float).reshape(-1, 4),
                            confidence=np.array(confs, dtype=float),
                            class_id=np.zeros(len(confs), dtype=int))
        det = tracker.update(det)
        det = det[det.tracker_id != -1]

        corte = frame[y0:y1]
        esc = args.largura / corte.shape[1]
        vis = cv2.resize(corte, (args.largura, int(round(corte.shape[0] * esc))), interpolation=cv2.INTER_AREA)

        for j, tid in enumerate(det.tracker_id):
            x1, y1b, x2, y2b = det.xyxy[j]
            p1 = (int(x1 * esc), int((y1b - y0) * esc))
            p2 = (int(x2 * esc), int((y2b - y0) * esc))
            centro = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            r = rastros.setdefault(int(tid), [])
            r.append(centro)
            del r[:-14]
            for k in range(1, len(r)):
                cv2.line(vis, r[k - 1], r[k], CESTA, 1, cv2.LINE_AA)
            cv2.rectangle(vis, p1, p2, CESTA, 2)
            cv2.putText(vis, f"#{int(tid)}", (p1[0], max(11, p1[1] - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, CESTA, 1, cv2.LINE_AA)

        etq = f"{(idx - i0) / fps_src:4.1f}s   cestas rastreadas: {len(det)}"
        cv2.rectangle(vis, (0, vis.shape[0] - 26), (vis.shape[1], vis.shape[0]), (24, 20, 15), -1)
        cv2.putText(vis, etq, (10, vis.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (235, 235, 235), 1, cv2.LINE_AA)

        quadros.append(Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)))
        if len(quadros) % 10 == 0:
            print(f"  {len(quadros)} quadros...")

    cap.release()
    if not quadros:
        sys.exit("nenhum quadro gerado")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    quadros[0].save(SAIDA, save_all=True, append_images=quadros[1:], format="WEBP",
                    duration=int(1000 / args.fps), loop=0, quality=args.qualidade, method=6)
    mb = SAIDA.stat().st_size / 1_048_576
    print(f"{len(quadros)} quadros  {quadros[0].size[0]}x{quadros[0].size[1]}  {mb:.1f} MB -> {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
