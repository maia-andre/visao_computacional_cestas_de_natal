"""Persistência de eventos em SQLite.

Cada evento (cruzamento de linha ou transição de zona) vira uma linha na
tabela `eventos`. O banco é a "trilha de auditoria": tudo o que o painel
mostra vem daqui.

`direcao` guarda:
- modo linha:  'in' | 'out'
- modo zonas:  'paletes->bancada', 'bancada->fora', ...

`anulado = 1` marca pares de vai-e-volta (A->B seguido de B->A do mesmo
objeto em poucos segundos). Ficam no banco para auditoria, mas saem da soma.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS eventos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,   -- ISO 8601, hora local (relógio do computador)
    camera      TEXT    NOT NULL,   -- ex.: 'tenda'
    sessao      TEXT    NOT NULL,   -- identifica a execução (vídeo/dia)
    track_id    INTEGER NOT NULL,   -- id do objeto dado pelo tracker
    classe      TEXT    NOT NULL,   -- ex.: 'cesta', 'person'
    direcao     TEXT    NOT NULL,   -- 'in'/'out' ou 'zonaA->zonaB'
    frame       INTEGER NOT NULL,   -- índice do frame no vídeo
    tempo_s     REAL,               -- segundo do vídeo (frame / fps)
    confianca   REAL,
    snapshot    TEXT,               -- caminho do frame salvo (opcional)
    anulado     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_eventos_sessao ON eventos (sessao);
CREATE INDEX IF NOT EXISTS idx_eventos_camera ON eventos (camera, timestamp);
"""

# colunas adicionadas depois da primeira versão — migração para bancos antigos
_COLUNAS_NOVAS = {
    "tempo_s": "REAL",
    "anulado": "INTEGER NOT NULL DEFAULT 0",
}


class EventStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self._migrar()

    def _migrar(self) -> None:
        existentes = {row[1] for row in self.conn.execute("PRAGMA table_info(eventos)")}
        for coluna, tipo in _COLUNAS_NOVAS.items():
            if coluna not in existentes:
                self.conn.execute(f"ALTER TABLE eventos ADD COLUMN {coluna} {tipo}")
        self.conn.commit()

    def registrar(
        self,
        *,
        camera: str,
        sessao: str,
        track_id: int,
        classe: str,
        direcao: str,
        frame: int,
        tempo_s: float | None = None,
        confianca: float | None = None,
        snapshot: str | None = None,
        anulado: bool = False,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO eventos (timestamp, camera, sessao, track_id, classe, direcao, frame,"
            " tempo_s, confianca, snapshot, anulado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                camera, sessao, int(track_id), classe, direcao, int(frame),
                tempo_s, confianca, snapshot, int(anulado),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def registrar_transicao(
        self,
        *,
        camera: str,
        sessao: str,
        track_id: int,
        classe: str,
        de: str,
        para: str,
        frame: int,
        tempo_s: float,
        vai_e_volta_s: float,
        confianca: float | None = None,
        snapshot: str | None = None,
    ) -> tuple[int, bool]:
        """Registra `de->para` aplicando a regra de vai-e-volta.

        Se o último evento não anulado deste objeto foi exatamente `para->de`
        há no máximo `vai_e_volta_s` segundos (tempo de vídeo), os dois ficam
        marcados como anulados: o objeto foi ajeitado, não movimentado.
        Devolve (id do evento, anulado?).
        """
        anulado = False
        anterior = self.conn.execute(
            "SELECT id, direcao, tempo_s FROM eventos"
            " WHERE sessao = ? AND track_id = ? AND anulado = 0 ORDER BY id DESC LIMIT 1",
            (sessao, int(track_id)),
        ).fetchone()
        if anterior is not None:
            ant_id, ant_direcao, ant_tempo = anterior
            if ant_direcao == f"{para}->{de}" and ant_tempo is not None and (tempo_s - ant_tempo) <= vai_e_volta_s:
                self.conn.execute("UPDATE eventos SET anulado = 1 WHERE id = ?", (ant_id,))
                anulado = True

        evento_id = self.registrar(
            camera=camera, sessao=sessao, track_id=track_id, classe=classe, direcao=f"{de}->{para}",
            frame=frame, tempo_s=tempo_s, confianca=confianca, snapshot=snapshot, anulado=anulado,
        )
        return evento_id, anulado

    def resumo(self, sessao: str) -> dict[str, int]:
        """Contagem por direção, já sem os anulados."""
        rows = self.conn.execute(
            "SELECT direcao, COUNT(*) FROM eventos WHERE sessao = ? AND anulado = 0 GROUP BY direcao",
            (sessao,),
        ).fetchall()
        return {direcao: n for direcao, n in rows}

    def close(self) -> None:
        self.conn.close()
