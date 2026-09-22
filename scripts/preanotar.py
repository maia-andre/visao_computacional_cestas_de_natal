"""Pré-anotação zero-shot dos frames e envio como *predictions* para o Label Studio.

    .\\rodar.cmd scripts\\preanotar.py --previa 5
    .\\rodar.cmd scripts\\preanotar.py --token SEU_TOKEN [--projeto 1] [--url http://localhost:8080]

Usa o YOLO-World (detector que aceita texto em vez de classes fixas) com o prompt
"box" e envia cada caixa encontrada como sugestão da classe `cesta` para a tarefa
correspondente no Label Studio. O anotador só corrige (apaga falsos, divide pilhas,
ajusta). Caixas cujo centro está acima de `--ignorar-acima` (fração da altura) são
descartadas: nesses vídeos o fundo do galpão fica no terço superior do quadro.
Confiança baixa de propósito (0,05): apagar uma caixa errada é mais rápido que desenhar uma que faltou.

`--previa N` só desenha N frames em data/dataset/preanot_previa/ e não envia nada.
Token: Account & Settings -> Access Token (aceita token legado ou personal access token).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import unquote

import cv2
import requests
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parents[1]
FRAMES = RAIZ / "data" / "dataset" / "frames"
PREVIA = RAIZ / "data" / "dataset" / "preanot_previa"
MODELO = "yolov8s-worldv2.pt"
PROMPT = "box"
VERSAO = "yolo-world-box-v1"


def detectar(modelo: YOLO, caminho: Path, conf: float, ignorar_acima: float) -> list[tuple[float, float, float, float, float]]:
    """Retorna caixas (x, y, w, h em % da imagem, conf) já filtradas."""
    r = modelo.predict(str(caminho), conf=conf, imgsz=1920, agnostic_nms=True, verbose=False)[0]
    h, w = r.orig_shape
    saida = []
    for b in r.boxes:
        x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
        if (y1 + y2) / 2 < ignorar_acima * h:
            continue
        saida.append((100 * x1 / w, 100 * y1 / h, 100 * (x2 - x1) / w, 100 * (y2 - y1) / h, float(b.conf)))
    return saida


class LabelStudio:
    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.s = requests.Session()
        self.refresh = token if token.count(".") == 2 else None  # personal access token (JWT)
        if self.refresh:
            self._renovar()
        else:
            self.s.headers["Authorization"] = f"Token {token}"

    def _renovar(self) -> None:
        """O access token do JWT expira em minutos; troca o refresh por um novo."""
        r = self.s.post(f"{self.url}/api/token/refresh", json={"refresh": self.refresh}, timeout=30)
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access']}"

    def _req(self, metodo: str, rota: str, **kw) -> requests.Response:
        r = self.s.request(metodo, f"{self.url}{rota}", timeout=60, **kw)
        if r.status_code == 401 and self.refresh:
            self._renovar()
            r = self.s.request(metodo, f"{self.url}{rota}", timeout=60, **kw)
        r.raise_for_status()
        return r

    def config(self, projeto: int) -> tuple[str, str]:
        """(from_name, to_name) do template de retângulos do projeto."""
        cfg = self._req("GET", f"/api/projects/{projeto}").json()["parsed_label_config"]
        nome, info = next((k, v) for k, v in cfg.items() if v["type"] == "RectangleLabels")
        return nome, info["to_name"][0]

    def tarefas(self, projeto: int) -> dict[str, tuple[int, bool]]:
        """Mapa nome-do-arquivo -> (id da tarefa, já tem alguma predição)."""
        mapa: dict[str, tuple[int, bool]] = {}
        pagina = 1
        while True:
            r = self.s.get(f"{self.url}/api/tasks", params={"project": projeto, "page": pagina, "page_size": 100}, timeout=60)
            if r.status_code == 404:
                break
            r.raise_for_status()
            itens = r.json()["tasks"]
            if not itens:
                break
            for t in itens:
                # a URL vem como /data/local-files/?d=frames%5Cpasta%5Carquivo.jpg
                nome = unquote(t["data"]["image"]).replace("\\", "/").rsplit("/", 1)[-1]
                mapa[nome] = (t["id"], (t.get("total_predictions") or 0) > 0)
            pagina += 1
        return mapa

    def enviar(self, tarefa: int, from_name: str, to_name: str, w: int, h: int,
               caixas: list[tuple[float, float, float, float, float]]) -> None:
        resultado = [
            {
                "from_name": from_name, "to_name": to_name, "type": "rectanglelabels",
                "original_width": w, "original_height": h, "image_rotation": 0,
                "value": {"x": x, "y": y, "width": bw, "height": bh, "rotation": 0, "rectanglelabels": ["cesta"]},
                "score": c,
            }
            for x, y, bw, bh, c in caixas
        ]
        score = min((c for *_, c in caixas), default=0.0)
        self._req("POST", "/api/predictions",
                  json={"task": tarefa, "model_version": VERSAO, "score": score, "result": resultado})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--token", default=os.environ.get("LABEL_STUDIO_TOKEN"))
    ap.add_argument("--projeto", type=int, default=1)
    ap.add_argument("--conf", type=float, default=0.05)
    ap.add_argument("--ignorar-acima", type=float, default=0.30)
    ap.add_argument("--previa", type=int, default=0, help="só desenha N frames, não envia")
    args = ap.parse_args()

    frames = sorted(FRAMES.rglob("*.jpg"))
    if not frames:
        sys.exit(f"nenhum frame em {FRAMES}")
    modelo = YOLO(MODELO)
    modelo.set_classes([PROMPT])

    if args.previa:
        PREVIA.mkdir(parents=True, exist_ok=True)
        passo = max(1, len(frames) // args.previa)
        for f in frames[::passo][: args.previa]:
            img = cv2.imread(str(f))
            h, w = img.shape[:2]
            caixas = detectar(modelo, f, args.conf, args.ignorar_acima)
            for x, y, bw, bh, c in caixas:
                p1 = (int(x * w / 100), int(y * h / 100))
                p2 = (int((x + bw) * w / 100), int((y + bh) * h / 100))
                cv2.rectangle(img, p1, p2, (0, 200, 0), 3)
                cv2.putText(img, f"{c:.2f}", p1, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
            cv2.imwrite(str(PREVIA / f.name), img)
            print(f"{f.name}: {len(caixas)} caixas")
        print(f"prévias em {PREVIA.relative_to(RAIZ)}")
        return

    if not args.token:
        sys.exit("informe --token ou a variável LABEL_STUDIO_TOKEN")
    ls = LabelStudio(args.url, args.token)
    from_name, to_name = ls.config(args.projeto)
    tarefas = ls.tarefas(args.projeto)
    print(f"{len(tarefas)} tarefas no projeto {args.projeto}; {len(frames)} frames locais")

    enviados = total = pulados = 0
    for f in frames:
        tarefa, feita = tarefas.get(f.name, (None, False))
        if tarefa is None:
            print(f"  sem tarefa: {f.name}")
            continue
        if feita:
            pulados += 1
            continue
        h, w = cv2.imread(str(f)).shape[:2]
        caixas = detectar(modelo, f, args.conf, args.ignorar_acima)
        ls.enviar(tarefa, from_name, to_name, w, h, caixas)
        enviados += 1
        total += len(caixas)
        if enviados % 20 == 0:
            print(f"  {enviados} tarefas, {total} caixas...")
    print(f"pronto: {enviados} tarefas com predições ({total} caixas, média {total / max(enviados, 1):.1f}/frame); {pulados} já tinham")


if __name__ == "__main__":
    main()
