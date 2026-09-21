"""Baixa vídeos de exemplo (da biblioteca supervision) para o teste zero.

    python scripts/baixar_video_exemplo.py            # baixa 'people-walking' (padrão)
    python scripts/baixar_video_exemplo.py vehicles   # outro
    python scripts/baixar_video_exemplo.py --listar

Os arquivos vão para data/videos/.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from supervision.assets import VideoAssets, download_assets

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "data" / "videos"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("nome", nargs="?", default="people-walking")
    p.add_argument("--listar", action="store_true")
    args = p.parse_args()

    ativos = {a.value.replace(".mp4", ""): a for a in VideoAssets}
    if args.listar:
        for n in sorted(ativos):
            print(n)
        return

    if args.nome not in ativos:
        raise SystemExit(f"desconhecido: {args.nome}. Use --listar.")

    DESTINO.mkdir(parents=True, exist_ok=True)
    os.chdir(DESTINO)  # download_assets grava no diretório atual
    caminho = download_assets(ativos[args.nome])
    print(f"salvo em: {DESTINO / Path(caminho).name}")


if __name__ == "__main__":
    main()
