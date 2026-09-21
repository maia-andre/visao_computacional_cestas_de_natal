"""Mostra o que está no banco de eventos.

    python scripts/ver_eventos.py            # resumo por sessão
    python scripts/ver_eventos.py --sessao people-walking_20260914_101500 --ultimos 20
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=str(RAIZ / "data" / "db" / "eventos.sqlite"))
    p.add_argument("--sessao", default=None)
    p.add_argument("--ultimos", type=int, default=0, help="listar os N últimos eventos da sessão")
    args = p.parse_args()

    if not Path(args.db).exists():
        raise SystemExit(f"banco não existe ainda: {args.db}")
    conn = sqlite3.connect(args.db)

    if args.sessao is None:
        print(f"{'sessao':45} {'camera':18} {'in':>6} {'out':>6}  primeiro → último")
        for row in conn.execute(
            "SELECT sessao, camera,"
            " SUM(direcao='in'), SUM(direcao='out'), MIN(timestamp), MAX(timestamp)"
            " FROM eventos GROUP BY sessao, camera ORDER BY MIN(timestamp)"
        ):
            s, cam, n_in, n_out, t0, t1 = row
            print(f"{s:45} {cam:18} {n_in:6d} {n_out:6d}  {t0} → {t1}")
        return

    resumo = conn.execute(
        "SELECT classe, direcao, COUNT(*) FROM eventos WHERE sessao=? GROUP BY classe, direcao",
        (args.sessao,),
    ).fetchall()
    print(f"sessão {args.sessao}")
    for classe, direcao, n in resumo:
        print(f"  {classe:12} {direcao:4} {n}")

    if args.ultimos:
        print()
        for row in conn.execute(
            "SELECT id, timestamp, frame, classe, track_id, direcao, confianca, snapshot"
            " FROM eventos WHERE sessao=? ORDER BY id DESC LIMIT ?",
            (args.sessao, args.ultimos),
        ):
            print("  ", row)


if __name__ == "__main__":
    main()
