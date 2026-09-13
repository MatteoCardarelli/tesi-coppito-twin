"""Sessioni sintetiche con risposta nota: i log reali non sono nella repository"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from coppito_analysis.loading import deduplica_timestamp
from coppito_analysis.sessione import Referto, Sessione

SAMPLING_HZ = 20.0
FPS = 60.0
QUOTA_Z = 98.1
VELOCITA_CMS = 140.0


def crea_sessione(t, x, y, eventi=None, session_id="SINT", **meta):
    """Una Sessione sana costruita da una traiettoria"""

    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(t)

    passi = np.hypot(np.diff(x), np.diff(y))
    velocita = passi / np.diff(t)
    stream = pd.DataFrame({
        "t": t,
        "pos_x": x,
        "pos_y": y,
        "pos_z": QUOTA_Z,
        "cam_yaw": 0.0,
        "cam_pitch": 0.0,
        "speed": np.concatenate(([velocita[0]], velocita)),
        "fps": FPS,
    })

    if eventi is None:
        eventi = [
            (t[0], "TASK_START", ""),
            (t[n // 3], "BARRIER_REACH", ""),
            (t[n // 2], "BARRIER_DEPART", ""),
            (t[2 * n // 3], "FORK_ENTER", "left"),
            (t[-1], "TASK_END", ""),
        ]
    tempi = np.array([evento[0] for evento in eventi], dtype=float)
    tabella_eventi = pd.DataFrame({
        "t": tempi,
        "event": [evento[1] for evento in eventi],
        "value": [evento[2] for evento in eventi],
        "pos_x": np.interp(tempi, t, x),
        "pos_y": np.interp(tempi, t, y),
        "pos_z": QUOTA_Z,
    })

    metadati = {
        "participant_id": session_id,
        "condition": "blocked",
        "sampling_hz": SAMPLING_HZ,
        "session_duration_s": float(t[-1] - t[0] + 1 / SAMPLING_HZ),
        "stream_rows": n,
        "event_rows": len(tabella_eventi),
        "min_path_cm": float(passi.sum()),
        "max_speed_cms": 140.0,
        "barrier_pos": [0.0, 0.0, QUOTA_Z],
        "fork_pos": [0.0, 0.0, QUOTA_Z],
    }
    metadati.update(meta)

    return Sessione(
        session_id=session_id,
        meta=metadati,
        stream_raw=stream,
        stream=deduplica_timestamp(stream),
        eventi=tabella_eventi,
        referto=Referto(session_id),
    )


def rettilineo(durata_s):
    """Rettilineo lungo x a 140 cm/s, campionato a 20 Hz: restituisce t, x, y"""

    t = np.linspace(0.0, durata_s, round(durata_s * SAMPLING_HZ) + 1)
    return t, VELOCITA_CMS * t, np.zeros_like(t)


def percorso(tratti):
    """Traiettoria a tratti: ("dritto", s), ("fermo", s), ("indietro", s), ("curva", gradi, s)"""

    passo = 0.001
    x = y = direzione = 0.0
    tempi, xs, ys = [0.0], [0.0], [0.0]

    for tratto in tratti:
        tipo, durata = tratto[0], tratto[-1]
        if tipo == "indietro":
            direzione += 180.0
        rotazione = tratto[1] if tipo == "curva" else 0.0
        velocita = 0.0 if tipo == "fermo" else VELOCITA_CMS

        for _ in range(round(durata / passo)):
            direzione += rotazione * passo / durata
            x += velocita * np.cos(np.radians(direzione)) * passo
            y += velocita * np.sin(np.radians(direzione)) * passo
            tempi.append(tempi[-1] + passo)
            xs.append(x)
            ys.append(y)

    t = np.arange(0.0, tempi[-1], 1 / SAMPLING_HZ)
    return t, np.interp(t, tempi, xs), np.interp(t, tempi, ys)


def scrivi_sessione(cartella, sessione):
    """Scrive i tre file della sessione come li scrive il logger"""

    cartella = Path(cartella)
    sessione.stream_raw.to_csv(cartella / f"{sessione.session_id}_stream.csv", index=False)
    sessione.eventi.to_csv(cartella / f"{sessione.session_id}_events.csv", index=False)
    (cartella / f"{sessione.session_id}_meta.json").write_text(
        json.dumps(sessione.meta), encoding="utf-8"
    )
