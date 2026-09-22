"""Conta objetos num vídeo / webcam / câmera IP, por linha virtual ou por zonas.

Exemplos:

    # Fase 0 — linha: vídeo de exemplo, conta pessoas cruzando o meio do frame
    .\\rodar.cmd scripts\\contar.py --fonte data\\videos\\people-walking.mp4 --classes person

    # linha vertical, contando carros, salvando vídeo anotado
    .\\rodar.cmd scripts\\contar.py --fonte data\\videos\\vehicles.mp4 --classes car truck ^
        --linha 0.5,0,0.5,1 --saida-video data\\saida\\vehicles_anotado.mp4

    # Tenda — zonas: desenhe antes com scripts\\definir_zonas.py
    .\\rodar.cmd scripts\\contar.py --fonte data\\videos\\ensaio_tenda_01.mp4 --classes cesta ^
        --modelo runs\\cestas_v1\\weights\\best.pt --zonas data\\zonas\\tenda.json --camera tenda

    # webcam do notebook, sem filtro de classe
    .\\rodar.cmd scripts\\contar.py --fonte 0 --pular 2

    # câmera IP (RTSP)
    .\\rodar.cmd scripts\\contar.py --fonte rtsp://usuario:senha@192.168.0.10:554/stream1 --classes cesta

Tecla `q` fecha a janela.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cestas.pipeline import ConfigContador, Contador, LinhaVirtual  # noqa: E402
from cestas.zonas import carregar_zonas  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fonte", required=True, help="caminho do vídeo, índice da webcam (0) ou URL rtsp://")
    p.add_argument("--modelo", default="yolov8n.pt", help="pesos YOLO (.pt). Padrão: yolov8n.pt (COCO)")
    p.add_argument("--classes", nargs="*", default=[], help="nomes de classe a contar (vazio = todas)")
    p.add_argument("--prompt", nargs="*", default=[],
                   help="YOLO-World: define as classes por texto (ex.: --prompt box). Exige pesos *-world*.pt")
    p.add_argument("--imgsz", type=int, default=640,
                   help="lado maior na inferência. Suba (1280/1920) quando o objeto é pequeno no quadro")
    p.add_argument("--largura-max", type=float, default=100.0,
                   help="descarta detecção mais larga que isso (%% do quadro). Útil contra móveis/estruturas")
    p.add_argument("--track-conf", type=float, default=None,
                   help="confiança que INICIA um track. Padrão max(--conf, 0.5); baixe para detector zero-shot")
    p.add_argument("--track-buffer", type=float, default=1.0,
                   help="segundos que um track sobrevive sem detecção (oclusão, borrão de movimento)")
    p.add_argument("--conf", type=float, default=0.35, help="confiança mínima da detecção")

    regra = p.add_argument_group("regra espacial (linha OU zonas)")
    regra.add_argument("--linha", default="0,0.5,1,0.5",
                       help="x1,y1,x2,y2 — frações do frame (0-1) ou pixels. Padrão: horizontal no meio")
    regra.add_argument("--zonas", default=None, help="JSON de zonas (ver scripts/definir_zonas.py). Ativa o modo zonas")
    regra.add_argument("--confirmacao", type=int, default=3,
                       help="modo zonas: frames seguidos numa zona nova antes de aceitar a transição")
    regra.add_argument("--vai-e-volta", type=float, default=4.0,
                       help="modo zonas: A->B seguido de B->A do mesmo objeto em até N s se anulam")

    p.add_argument("--camera", default="camera0_teste", help="nome lógico da câmera para o banco")
    p.add_argument("--sessao", default=None, help="nome da sessão (padrão: nome do vídeo + hora)")
    p.add_argument("--db", default=str(RAIZ / "data" / "db" / "eventos.sqlite"))
    p.add_argument("--snapshots", action="store_true", help="salvar o frame anotado de cada evento em data/snapshots/<sessao>/")
    p.add_argument("--saida-video", default=None, help="gravar vídeo anotado neste caminho (.mp4)")
    p.add_argument("--sem-janela", action="store_true", help="não abrir janela (útil em servidor/headless)")
    p.add_argument("--pular", type=int, default=1,
                   help="processar 1 a cada N frames (ex.: 3). Alivia CPU fraca / webcam ao vivo")
    args = p.parse_args()

    fonte: str | int = int(args.fonte) if args.fonte.isdigit() else args.fonte
    nome_fonte = f"webcam{fonte}" if isinstance(fonte, int) else Path(str(fonte)).stem
    sessao = args.sessao or f"{nome_fonte}_{datetime.now():%Y%m%d_%H%M%S}"

    cfg = ConfigContador(
        modelo=args.modelo,
        classes=args.classes,
        prompt=args.prompt,
        imgsz=args.imgsz,
        largura_max=args.largura_max,
        track_conf=args.track_conf,
        track_buffer_s=args.track_buffer,
        confianca=args.conf,
        linha=LinhaVirtual.parse(args.linha),
        zonas=carregar_zonas(args.zonas) if args.zonas else None,
        frames_confirmacao=args.confirmacao,
        vai_e_volta_s=args.vai_e_volta,
        camera=args.camera,
        sessao=sessao,
        db_path=Path(args.db),
        snapshots_dir=(RAIZ / "data" / "snapshots" / sessao) if args.snapshots else None,
        mostrar=not args.sem_janela,
        saida_video=Path(args.saida_video) if args.saida_video else None,
        pular=max(args.pular, 1),
    )
    Contador(cfg).executar(fonte)


if __name__ == "__main__":
    main()
