"""Pipeline: detecção → tracking → (linha virtual | zonas) → evento.

    frame ──► YOLO (detecta) ──► ByteTrack (dá identidade) ──► regra espacial ──► SQLite

Dois modos, escolhidos pela configuração:

- **linha**  (Fase 0): um segmento; evento quando o centro da caixa cruza (in/out).
- **zonas**  (tenda):  polígonos nomeados; evento quando o objeto muda de zona
                       (ex.: `paletes->bancada`). Ver `zonas.py`.

Nada aqui sabe o que é uma "cesta". O modelo e as classes são parâmetros:
na Fase 0 usamos o YOLO pré-treinado (COCO) e contamos pessoas/garrafas só
para provar o encanamento. Na Fase 2 trocamos o modelo por um treinado com o
nosso dataset e a classe passa a ser `cesta`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from trackers import ByteTrackTracker
from ultralytics import YOLO

from .db import EventStore
from .zonas import MonitorZonas, Transicao, ZonaDef


@dataclass
class LinhaVirtual:
    """Segmento (x1, y1) → (x2, y2). Valores em [0, 1] são frações do frame."""

    x1: float
    y1: float
    x2: float
    y2: float

    @classmethod
    def parse(cls, texto: str) -> "LinhaVirtual":
        partes = [float(p) for p in texto.split(",")]
        if len(partes) != 4:
            raise ValueError("linha deve ser 'x1,y1,x2,y2'")
        return cls(*partes)

    def em_pixels(self, largura: int, altura: int) -> tuple[sv.Point, sv.Point]:
        coords = [self.x1, self.y1, self.x2, self.y2]
        if all(0.0 <= c <= 1.0 for c in coords):
            coords = [self.x1 * largura, self.y1 * altura, self.x2 * largura, self.y2 * altura]
        x1, y1, x2, y2 = (int(round(c)) for c in coords)
        return sv.Point(x1, y1), sv.Point(x2, y2)


@dataclass
class ConfigContador:
    modelo: str = "yolov8n.pt"
    classes: list[str] = field(default_factory=list)  # vazio = todas
    prompt: list[str] = field(default_factory=list)   # YOLO-World: classes por texto (ex.: ["box"])
    imgsz: int = 640                                  # lado maior na inferência; suba para objeto pequeno
    largura_max: float = 100.0                        # descarta detecção mais larga que isso (% do quadro)
    track_conf: float | None = None                   # confiança que INICIA um track (None = max(confianca, 0.5))
    track_buffer_s: float = 1.0                       # por quantos segundos um track sobrevive sem detecção
    confianca: float = 0.35
    # modo linha (padrão) ...
    linha: LinhaVirtual = field(default_factory=lambda: LinhaVirtual(0.0, 0.5, 1.0, 0.5))
    # ... ou modo zonas (se `zonas` não for None, a linha é ignorada)
    zonas: list[ZonaDef] | None = None
    frames_confirmacao: int = 3       # frames seguidos numa zona nova antes de aceitar
    vai_e_volta_s: float = 4.0        # A->B e B->A do mesmo objeto em < N s se anulam
    camera: str = "camera0_teste"
    sessao: str = "teste"
    db_path: Path = Path("data/db/eventos.sqlite")
    snapshots_dir: Path | None = None  # se definido, salva o frame de cada evento
    mostrar: bool = True
    saida_video: Path | None = None
    pular: int = 1  # processa 1 a cada N frames (CPU fraca / webcam ao vivo)

    @property
    def modo(self) -> str:
        return "zonas" if self.zonas else "linha"


class Contador:
    def __init__(self, cfg: ConfigContador):
        self.cfg = cfg
        self.model = YOLO(cfg.modelo)
        # YOLO-World aceita as classes como texto. Tem de vir antes de ler `names`,
        # que passa a ser o próprio prompt.
        if cfg.prompt:
            self.model.set_classes(cfg.prompt)
        self.nome_por_id: dict[int, str] = self.model.names
        self.ids_classes: list[int] | None = None
        if cfg.classes:
            inv = {v: k for k, v in self.nome_por_id.items()}
            faltando = [c for c in cfg.classes if c not in inv]
            if faltando:
                raise ValueError(f"classes não existem no modelo: {faltando}. Disponíveis: {sorted(inv)}")
            self.ids_classes = [inv[c] for c in cfg.classes]

        self.store = EventStore(cfg.db_path)
        self.tracker: ByteTrackTracker | None = None
        self.linha: sv.LineZone | None = None
        self.monitor: MonitorZonas | None = None
        self.fps = 30.0

        self.box_annotator = sv.BoxAnnotator(thickness=2)
        self.label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
        self.trace_annotator = sv.TraceAnnotator(trace_length=30)
        self.line_annotator = sv.LineZoneAnnotator(thickness=2, text_thickness=1, text_scale=0.7)
        self.zone_annotators: list[sv.PolygonZoneAnnotator] = []

    # ------------------------------------------------------------------ #
    def _preparar(self, largura: int, altura: int, fps: float) -> None:
        self.fps = fps if fps > 0 else 30.0
        fps_efetivo = self.fps / max(self.cfg.pular, 1)
        # track_activation_threshold baixo: a confiança mínima já foi aplicada no YOLO.
        # `high_conf_det_threshold` é o que decide se uma detecção pode INICIAR um
        # track (as mais fracas só ajudam a manter os que já existem). O padrão de 0,5
        # é alto demais para detector zero-shot, cuja confiança em cesta fica em
        # 0,26-0,64: quase nenhum track nasce e nenhuma transição acontece.
        self.tracker = ByteTrackTracker(
            frame_rate=fps_efetivo,
            track_activation_threshold=self.cfg.confianca,
            high_conf_det_threshold=(self.cfg.track_conf if self.cfg.track_conf is not None
                                     else max(self.cfg.confianca, 0.5)),
            lost_track_buffer=max(1, int(fps_efetivo * self.cfg.track_buffer_s)),
        )
        if self.cfg.modo == "zonas":
            self.monitor = MonitorZonas(
                self.cfg.zonas, largura, altura,
                frames_confirmacao=self.cfg.frames_confirmacao,
                frames_esquecer=int(fps_efetivo * 5),
            )
            self.zone_annotators = self.monitor.anotadores()
        else:
            inicio, fim = self.cfg.linha.em_pixels(largura, altura)
            # Só o CENTRO da caixa dispara o cruzamento: evita contar quando
            # apenas a borda do objeto (ou uma mão) encosta na linha.
            self.linha = sv.LineZone(start=inicio, end=fim, triggering_anchors=[sv.Position.CENTER])

    def _detectar(self, frame: np.ndarray) -> sv.Detections:
        result = self.model(frame, conf=self.cfg.confianca, classes=self.ids_classes,
                            imgsz=self.cfg.imgsz, verbose=False)[0]
        dets = sv.Detections.from_ultralytics(result)
        if self.cfg.largura_max < 100.0 and len(dets):
            # Mesmo falso positivo da pré-anotação: móveis/estruturas do fundo que
            # atravessam o quadro. Ver docs/03_fase2_modelo.md.
            larguras = (dets.xyxy[:, 2] - dets.xyxy[:, 0]) * 100.0 / frame.shape[1]
            dets = dets[larguras <= self.cfg.largura_max]
        return dets

    def _salvar_snapshot(self, frame_idx: int, track_id: int, rotulo: str, frame: np.ndarray) -> str | None:
        if self.cfg.snapshots_dir is None:
            return None
        self.cfg.snapshots_dir.mkdir(parents=True, exist_ok=True)
        nome = f"f{frame_idx:06d}_t{track_id}_{rotulo.replace('->', '_')}.jpg"
        caminho = str(self.cfg.snapshots_dir / nome)
        cv2.imwrite(caminho, frame)
        return caminho

    # ---- modo linha ---------------------------------------------------- #
    def _eventos_linha(self, dets: sv.Detections, frame_idx: int, frame: np.ndarray) -> list[str]:
        cruzou_in, cruzou_out = self.linha.trigger(dets)
        mensagens: list[str] = []
        for direcao, mascara in (("in", cruzou_in), ("out", cruzou_out)):
            for i in np.flatnonzero(mascara):
                track_id = int(dets.tracker_id[i])
                classe = self.nome_por_id[int(dets.class_id[i])]
                conf = float(dets.confidence[i]) if dets.confidence is not None else None
                self.store.registrar(
                    camera=self.cfg.camera, sessao=self.cfg.sessao, track_id=track_id, classe=classe,
                    direcao=direcao, frame=frame_idx, tempo_s=frame_idx / self.fps, confianca=conf,
                    snapshot=self._salvar_snapshot(frame_idx, track_id, direcao, frame),
                )
                sinal = "+1" if direcao == "in" else "-1"
                mensagens.append(f"[frame {frame_idx:6d}] {sinal} {classe} #{track_id} ({direcao})")
        return mensagens

    # ---- modo zonas ---------------------------------------------------- #
    def _eventos_zonas(self, dets: sv.Detections, frame_idx: int, frame: np.ndarray) -> list[str]:
        mensagens: list[str] = []
        for t in self.monitor.atualizar(dets, frame_idx, self.fps):
            mensagens.append(self._registrar_transicao(t, frame))
        return mensagens

    def _registrar_transicao(self, t: Transicao, frame: np.ndarray) -> str:
        classe = self.nome_por_id[t.classe_id]
        direcao = f"{t.de}->{t.para}"
        _, anulado = self.store.registrar_transicao(
            camera=self.cfg.camera, sessao=self.cfg.sessao, track_id=t.track_id, classe=classe,
            de=t.de, para=t.para, frame=t.frame, tempo_s=t.tempo_s, vai_e_volta_s=self.cfg.vai_e_volta_s,
            confianca=t.confianca, snapshot=self._salvar_snapshot(t.frame, t.track_id, direcao, frame),
        )
        marca = "  (vai-e-volta: anulado)" if anulado else ""
        return f"[frame {t.frame:6d} {t.tempo_s:7.1f}s] {classe} #{t.track_id}  {direcao}{marca}"

    # ---- desenho ------------------------------------------------------- #
    def _anotar(self, frame: np.ndarray, dets: sv.Detections) -> np.ndarray:
        out = frame.copy()
        for za in self.zone_annotators:
            out = za.annotate(out)
        labels = [
            f"#{tid} {self.nome_por_id[int(cid)]} {conf:.2f}"
            for tid, cid, conf in zip(dets.tracker_id, dets.class_id, dets.confidence)
        ]
        out = self.trace_annotator.annotate(out, dets)
        out = self.box_annotator.annotate(out, dets)
        out = self.label_annotator.annotate(out, dets, labels=labels)
        if self.linha is not None:
            out = self.line_annotator.annotate(out, line_counter=self.linha)
        return out

    def _cabecalho(self, fonte, largura, altura, fps, total) -> None:
        print(f"fonte={fonte!r} {largura}x{altura} @ {fps:.1f} fps" + (f" ({total} frames)" if total > 0 else ""))
        print(f"modelo={self.cfg.modelo} classes={self.cfg.classes or 'todas'} conf>={self.cfg.confianca}"
              f" imgsz={self.cfg.imgsz}" + (f" prompt={self.cfg.prompt}" if self.cfg.prompt else ""))
        if self.cfg.modo == "zonas":
            print(f"modo=zonas {self.monitor.nomes} + 'fora'  confirmacao={self.cfg.frames_confirmacao} frames"
                  f"  vai-e-volta<={self.cfg.vai_e_volta_s}s")
        else:
            print(f"modo=linha {self.cfg.linha}")
        print(f"pular={self.cfg.pular}  sessao={self.cfg.sessao}  db={self.cfg.db_path}")
        print("-" * 60)

    def _rodape(self, frame_idx: int) -> dict:
        resumo: dict = {"frames": frame_idx, "eventos": self.store.resumo(self.cfg.sessao)}
        print("-" * 60)
        print(f"frames processados: {frame_idx}")
        if self.cfg.modo == "zonas":
            print("transições (sem vai-e-volta):")
            for direcao, n in sorted(resumo["eventos"].items()):
                print(f"  {direcao:24} {n:5d}")
            resumo["na_zona_agora"] = self.monitor.contagem_atual()
            print(f"objetos em cada zona no último frame: {resumo['na_zona_agora']}")
        else:
            resumo["in"], resumo["out"] = self.linha.in_count, self.linha.out_count
            print(f"cruzamentos  in: {resumo['in']}   out: {resumo['out']}")
            print(f"no banco ({self.cfg.sessao}): {resumo['eventos']}")
        return resumo

    # ------------------------------------------------------------------ #
    def executar(self, fonte: str | int) -> dict:
        cap = cv2.VideoCapture(fonte)
        if not cap.isOpened():
            raise RuntimeError(f"não consegui abrir a fonte de vídeo: {fonte!r}")

        largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._preparar(largura, altura, fps)

        writer = None
        if self.cfg.saida_video is not None:
            self.cfg.saida_video.parent.mkdir(parents=True, exist_ok=True)
            writer = cv2.VideoWriter(
                str(self.cfg.saida_video), cv2.VideoWriter_fourcc(*"mp4v"),
                fps / max(self.cfg.pular, 1), (largura, altura),
            )

        self._cabecalho(fonte, largura, altura, fps, total)
        gerar_eventos = self._eventos_zonas if self.cfg.modo == "zonas" else self._eventos_linha

        frame_idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if self.cfg.pular > 1 and frame_idx % self.cfg.pular != 0:
                    frame_idx += 1
                    continue

                dets = self._detectar(frame)
                dets = self.tracker.update(dets)
                # O tracker devolve tracker_id == -1 para objetos ainda não confirmados
                # (vistos há menos de N frames). Sem identidade não há como saber se
                # "cruzou", então esses ficam fora da regra espacial e da tela.
                dets = dets[dets.tracker_id != -1]

                # Anota antes de registrar: o snapshot do evento leva caixas, ids e
                # zonas/linha — na auditoria, responde "qual objeto" sem reprocessar.
                anotado = self._anotar(frame, dets) if (self.cfg.mostrar or writer or self.cfg.snapshots_dir) else frame

                for msg in gerar_eventos(dets, frame_idx, anotado):
                    print(msg)

                if writer is not None:
                    writer.write(anotado)
                if self.cfg.mostrar:
                    cv2.imshow("Cestas (q para sair)", anotado)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                frame_idx += 1
        finally:
            cap.release()
            if writer is not None:
                writer.release()
            if self.cfg.mostrar:
                cv2.destroyAllWindows()

        resumo = self._rodape(frame_idx)
        self.store.close()
        return resumo
