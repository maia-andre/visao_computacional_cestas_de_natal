"""Teste sintético da lógica de zonas + vai-e-volta, sem modelo nem vídeo.

    .\\rodar.cmd scripts\\testar_zonas.py

Simula um objeto (#1) que vai de `paletes` para `bancada`, volta em 1 s
(deve anular), vai de novo e fica (deve contar 1), e depois sai para `fora`.
E um objeto (#2) que passa direto paletes -> fora (entrega direta).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import supervision as sv

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cestas.db import EventStore  # noqa: E402
from cestas.zonas import MonitorZonas, ZonaDef  # noqa: E402

W, H, FPS = 1000, 500, 10.0
ZONAS = [
    ZonaDef("paletes", [(0, 0), (400, 0), (400, 500), (0, 500)]),
    ZonaDef("bancada", [(400, 0), (700, 0), (700, 500), (400, 500)]),
]
VAI_E_VOLTA_S = 4.0


def det(track_id: int, cx: float, cy: float = 250) -> sv.Detections:
    return sv.Detections(
        xyxy=np.array([[cx - 20, cy - 20, cx + 20, cy + 20]], dtype=float),
        confidence=np.array([0.9]), class_id=np.array([0]), tracker_id=np.array([track_id]),
    )


def juntar(*ds: sv.Detections) -> sv.Detections:
    return sv.Detections.merge(list(ds)) if ds else sv.Detections.empty()


def main() -> None:
    monitor = MonitorZonas(ZONAS, W, H, frames_confirmacao=3, frames_esquecer=1000)
    store = EventStore(Path(tempfile.mkdtemp()) / "t.sqlite")
    sessao = "sintetico"

    # roteiro: (frame, [ (track, x) ])
    roteiro: list[tuple[int, list[tuple[int, float]]]] = []
    f = 0
    def passo(objs, n=1):
        nonlocal f
        for _ in range(n):
            roteiro.append((f, objs)); f += 1

    passo([(1, 200), (2, 200)], 5)      # ambos em paletes
    passo([(1, 550), (2, 200)], 5)      # #1 vai à bancada (0.5 s)   -> paletes->bancada
    passo([(1, 200), (2, 200)], 5)      # #1 volta 0.5 s depois      -> bancada->paletes (ANULA o par)
    passo([(1, 550), (2, 200)], 60)     # #1 vai e fica 6 s          -> paletes->bancada (conta)
    passo([(1, 850), (2, 850)], 5)      # #1 bancada->fora ; #2 paletes->fora (entrega direta)

    for frame_idx, objs in roteiro:
        dets = juntar(*[det(t, x) for t, x in objs])
        for t in monitor.atualizar(dets, frame_idx, FPS):
            _, anulado = store.registrar_transicao(
                camera="t", sessao=sessao, track_id=t.track_id, classe="cesta", de=t.de, para=t.para,
                frame=t.frame, tempo_s=t.tempo_s, vai_e_volta_s=VAI_E_VOLTA_S,
            )
            print(f"frame {t.frame:3d} {t.tempo_s:5.1f}s  #{t.track_id} {t.de}->{t.para}" + ("  (anulado)" if anulado else ""))

    resumo = store.resumo(sessao)
    print("\nresumo (sem anulados):", resumo)
    esperado = {"paletes->bancada": 1, "bancada->fora": 1, "paletes->fora": 1}
    assert resumo == esperado, f"esperado {esperado}, obtido {resumo}"
    total_anulados = store.conn.execute("SELECT COUNT(*) FROM eventos WHERE anulado=1").fetchone()[0]
    assert total_anulados == 2, total_anulados
    print("OK: vai-e-volta anulado, entrega direta contada, saldo correto")


if __name__ == "__main__":
    main()
