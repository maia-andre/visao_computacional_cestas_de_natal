"""Zonas: polígonos nomeados sobre o frame e a máquina de estados por objeto.

Em vez de "cruzou a linha?", a pergunta passa a ser "em que zona o objeto está?".
Um evento é uma TRANSIÇÃO: o objeto #17 estava em `paletes` e agora está em
`bancada`. Isso resolve três coisas que linha reta não resolve:

- bancada em "L" (qualquer polígono serve);
- vai-e-volta (a transição inversa é detectada e as duas se anulam);
- entrega direta palete → funcionário sem passar pela bancada (é só uma
  transição `paletes -> fora`, contada separadamente).

Arquivo de zonas (JSON), coordenadas em fração do frame (0–1) ou em pixels:

    {
      "zonas": [
        {"nome": "paletes", "pontos": [[0.05, 0.05], [0.45, 0.05], [0.45, 0.95], [0.05, 0.95]]},
        {"nome": "bancada", "pontos": [[0.45, 0.05], [0.70, 0.05], [0.70, 0.95], [0.45, 0.95]]}
      ]
    }

Tudo o que não está em zona nenhuma é a zona implícita `fora`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import supervision as sv

FORA = "fora"

_CORES = [
    sv.Color.from_hex("#ff9f1c"),  # laranja
    sv.Color.from_hex("#2ec4b6"),  # verde-água
    sv.Color.from_hex("#e71d36"),  # vermelho
    sv.Color.from_hex("#8338ec"),  # roxo
    sv.Color.from_hex("#3a86ff"),  # azul
]


@dataclass
class ZonaDef:
    nome: str
    pontos: list[tuple[float, float]]

    def em_pixels(self, largura: int, altura: int) -> np.ndarray:
        pts = np.array(self.pontos, dtype=float)
        if pts.max() <= 1.0:
            pts[:, 0] *= largura
            pts[:, 1] *= altura
        return pts.round().astype(np.int64)


def carregar_zonas(caminho: str | Path) -> list[ZonaDef]:
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    zonas = [ZonaDef(z["nome"], [tuple(p) for p in z["pontos"]]) for z in dados["zonas"]]
    nomes = [z.nome for z in zonas]
    if len(set(nomes)) != len(nomes):
        raise ValueError(f"nomes de zona repetidos: {nomes}")
    if FORA in nomes:
        raise ValueError(f"'{FORA}' é reservado para 'nenhuma zona'")
    for z in zonas:
        if len(z.pontos) < 3:
            raise ValueError(f"zona {z.nome!r} precisa de >= 3 pontos")
    return zonas


@dataclass
class Transicao:
    track_id: int
    de: str
    para: str
    frame: int
    tempo_s: float
    classe_id: int
    confianca: float | None


@dataclass
class _EstadoTrack:
    zona: str                 # zona confirmada
    candidata: str            # zona vista no último frame
    frames_na_candidata: int  # há quantos frames consecutivos está na candidata
    ultimo_frame: int


@dataclass
class MonitorZonas:
    """Mantém a zona confirmada de cada track e emite transições.

    `frames_confirmacao`: quantos frames consecutivos numa zona nova antes de
    aceitar a mudança. Evita disparar quando a caixa "treme" na borda.
    """

    defs: list[ZonaDef]
    largura: int
    altura: int
    frames_confirmacao: int = 3
    frames_esquecer: int = 150  # track sumiu há tanto tempo → esquece o estado

    zonas: dict[str, sv.PolygonZone] = field(init=False)
    _estado: dict[int, _EstadoTrack] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self.zonas = {
            d.nome: sv.PolygonZone(
                polygon=d.em_pixels(self.largura, self.altura),
                triggering_anchors=[sv.Position.CENTER],
            )
            for d in self.defs
        }

    @property
    def nomes(self) -> list[str]:
        return [d.nome for d in self.defs]

    def _zona_de_cada(self, dets: sv.Detections) -> list[str]:
        """Nome da zona do centro de cada detecção (primeira que contém; senão `fora`)."""
        n = len(dets)
        resultado = [FORA] * n
        if n == 0:
            return resultado
        for nome, zona in self.zonas.items():
            dentro = zona.trigger(dets)  # também atualiza zona.current_count
            for i in np.flatnonzero(dentro):
                if resultado[i] == FORA:
                    resultado[i] = nome
        return resultado

    def atualizar(self, dets: sv.Detections, frame_idx: int, fps: float) -> list[Transicao]:
        transicoes: list[Transicao] = []
        zonas_atuais = self._zona_de_cada(dets)

        for i, zona_vista in enumerate(zonas_atuais):
            tid = int(dets.tracker_id[i])
            est = self._estado.get(tid)
            if est is None:
                # Primeira vez que vemos o objeto: nasce na zona em que apareceu,
                # sem gerar transição (não sabemos de onde veio).
                self._estado[tid] = _EstadoTrack(zona_vista, zona_vista, 1, frame_idx)
                continue

            est.ultimo_frame = frame_idx
            if zona_vista == est.candidata:
                est.frames_na_candidata += 1
            else:
                est.candidata = zona_vista
                est.frames_na_candidata = 1

            if est.candidata != est.zona and est.frames_na_candidata >= self.frames_confirmacao:
                conf = float(dets.confidence[i]) if dets.confidence is not None else None
                transicoes.append(Transicao(
                    track_id=tid, de=est.zona, para=est.candidata, frame=frame_idx,
                    tempo_s=frame_idx / fps if fps > 0 else 0.0,
                    classe_id=int(dets.class_id[i]), confianca=conf,
                ))
                est.zona = est.candidata

        # limpeza de tracks antigos
        for tid in [t for t, e in self._estado.items() if frame_idx - e.ultimo_frame > self.frames_esquecer]:
            del self._estado[tid]

        return transicoes

    def contagem_atual(self) -> dict[str, int]:
        """Quantos objetos estão em cada zona neste instante (do último `atualizar`)."""
        return {nome: int(z.current_count) for nome, z in self.zonas.items()}

    def anotadores(self) -> list[sv.PolygonZoneAnnotator]:
        return [
            sv.PolygonZoneAnnotator(zone=z, color=_CORES[i % len(_CORES)], thickness=2,
                                    text_scale=0.6, text_thickness=1, opacity=0.08)
            for i, z in enumerate(self.zonas.values())
        ]
