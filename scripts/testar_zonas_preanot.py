"""Teste de contagem reaproveitando as detecções já calculadas na pré-anotação.

    .\\rodar.cmd scripts\\testar_zonas_preanot.py --video 01 --zonas data\\zonas\\almox_obliqua_teste.json

Roda tracking + zonas sobre as caixas que o `preanotar.py` já enviou ao Label
Studio, em vez de reprocessar o vídeo com o detector. Motivo: a detecção é a
parte cara (~4 s por frame nesta CPU, ~25 min por vídeo) e já foi paga uma vez.
Assim dá para iterar na regra espacial em segundos.

Limite conhecido: os frames da pré-anotação são 1 a cada 0,5 s (2 fps), contra
os 6 fps da leitura direta do vídeo. Menos frames = tracking mais difícil, então
o número que sai daqui é um piso, não o resultado final do pipeline.

Não substitui `contar.py`: serve para ajustar zonas e parâmetros de tracking
antes de gastar uma rodada completa.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote

import numpy as np
import supervision as sv

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cestas.zonas import FORA, MonitorZonas, carregar_zonas  # noqa: E402
from trackers import ByteTrackTracker  # noqa: E402

LS_DB = Path(os.path.expanduser("~/AppData/Local/label-studio/label-studio/label_studio.sqlite3"))


def carregar_predicoes(marca: str, largura: int, altura: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """[(nome_do_frame, xyxy em pixels, confianças)] ordenado por frame."""
    con = sqlite3.connect(LS_DB)
    por_frame: dict[str, tuple[list, list]] = {}
    for dados, resultado in con.execute(
        "select t.data, p.result from prediction p join task t on t.id = p.task_id"
    ):
        nome = unquote(next(iter(json.loads(dados).values()))).replace("\\", "/").rsplit("/", 1)[-1]
        if marca not in nome:
            continue
        caixas, confs = [], []
        for b in json.loads(resultado):
            v = b["value"]
            x1 = v["x"] * largura / 100
            y1 = v["y"] * altura / 100
            caixas.append([x1, y1, x1 + v["width"] * largura / 100, y1 + v["height"] * altura / 100])
            confs.append(float(b.get("score") or 0.0))
        por_frame[nome] = (caixas, confs)
    con.close()
    return [
        (nome, np.array(c, dtype=float).reshape(-1, 4), np.array(s, dtype=float))
        for nome, (c, s) in sorted(por_frame.items())
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="01", help="marca que identifica o vídeo no nome do frame")
    ap.add_argument("--zonas", default=str(RAIZ / "data" / "zonas" / "almox_obliqua_teste.json"))
    ap.add_argument("--largura", type=int, default=2160)
    ap.add_argument("--altura", type=int, default=3840)
    ap.add_argument("--fps", type=float, default=2.0, help="fps efetivo dos frames pré-anotados")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--track-conf", type=float, default=0.35)
    ap.add_argument("--track-buffer", type=float, default=1.5, help="segundos que um track sobrevive sem detecção")
    ap.add_argument("--confirmacao", type=int, default=2)
    ap.add_argument("--min-frames", type=int, default=2, help="frames para o tracker confirmar um track")
    args = ap.parse_args()

    frames = carregar_predicoes(f"_{args.video}_", args.largura, args.altura)
    if not frames:
        sys.exit(f"nenhuma predição encontrada para o vídeo {args.video!r} em {LS_DB}")

    tracker = ByteTrackTracker(
        frame_rate=args.fps,
        track_activation_threshold=args.conf,
        high_conf_det_threshold=args.track_conf,
        lost_track_buffer=max(1, int(args.fps * args.track_buffer)),
        minimum_consecutive_frames=args.min_frames,
    )
    monitor = MonitorZonas(
        carregar_zonas(args.zonas), args.largura, args.altura,
        frames_confirmacao=args.confirmacao, frames_esquecer=int(args.fps * 5),
    )

    print(f"{len(frames)} frames a {args.fps} fps  ({len(frames) / args.fps:.0f}s)  zonas={monitor.nomes}")
    print(f"conf>={args.conf}  track-conf={args.track_conf}  confirmacao={args.confirmacao}")
    print("-" * 60)

    contagem: dict[str, int] = {}
    tracks_vistos: set[int] = set()
    for i, (nome, xyxy, confs) in enumerate(frames):
        manter = confs >= args.conf
        dets = sv.Detections(
            xyxy=xyxy[manter].reshape(-1, 4),
            confidence=confs[manter],
            class_id=np.zeros(int(manter.sum()), dtype=int),
        )
        dets = tracker.update(dets)
        dets = dets[dets.tracker_id != -1]
        tracks_vistos.update(int(t) for t in dets.tracker_id)
        for t in monitor.atualizar(dets, i, args.fps):
            rotulo = f"{t.de}->{t.para}"
            contagem[rotulo] = contagem.get(rotulo, 0) + 1
            print(f"[{t.tempo_s:6.1f}s] #{t.track_id:<4} {rotulo}")

    print("-" * 60)
    print(f"tracks confirmados: {len(tracks_vistos)}")
    for rotulo, n in sorted(contagem.items()):
        print(f"  {rotulo:24} {n:4d}")
    print(f"na zona no último frame: {monitor.contagem_atual()}")


if __name__ == "__main__":
    main()
