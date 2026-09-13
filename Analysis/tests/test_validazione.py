"""Test dei controlli di qualità, sempre attraverso valida() (validazione.py)"""

import pandas as pd
import pytest

from coppito_analysis.sessione import ERROR, INFO, WARN
from coppito_analysis.validazione import valida
from tests.sintetici import crea_sessione, rettilineo


def sessione(eventi=None, **meta):
    """Rettilineo di 10 s (201 campioni), eventi indicati per indice di campione"""

    t, x, y = rettilineo(10.0)
    if eventi is not None:
        eventi = [(t[i], nome, valore) for i, nome, valore in eventi]
    return crea_sessione(t, x, y, eventi=eventi, **meta)


def colonna_mancante():
    s = sessione()
    s.stream_raw = s.stream_raw.drop(columns="cam_pitch")
    return s


def duplicato_con_posizione_diversa():
    s = sessione(stream_rows=202)
    copia = s.stream_raw.iloc[[0]].assign(pos_x=999.0)
    s.stream_raw = pd.concat([copia, s.stream_raw], ignore_index=True)
    return s


def buco_temporale():
    s = sessione(stream_rows=196)
    s.stream_raw = s.stream_raw.drop(index=range(50, 55))
    s.stream = s.stream.drop(index=range(50, 55)).reset_index(drop=True)
    return s


def eventi_vuoti():
    s = sessione(event_rows=0)
    s.eventi = s.eventi.iloc[0:0]
    return s


def metadati_vuoti():
    s = sessione()
    s.meta = {}
    return s


def fps_bassi():
    s = sessione()
    s.stream["fps"] = 25.0
    return s


SENZA_TASK_END = [(0, "TASK_START", ""), (67, "BARRIER_REACH", ""), (100, "BARRIER_DEPART", ""),
                  (134, "FORK_ENTER", "left")]

CASI = [
    pytest.param(sessione, [], id="sessione sana"),
    pytest.param(colonna_mancante, [(WARN, "COLONNE_MANCANTI")], id="colonna mancante"),
    pytest.param(duplicato_con_posizione_diversa, [(INFO, "DEDUPLICA"), (WARN, "DUPLICATI_INCOERENTI")],
                 id="duplicato con posizione diversa"),
    pytest.param(lambda: sessione(stream_rows=202), [(WARN, "CONTEGGIO_HEADER")], id="conteggio con intestazione"),
    pytest.param(buco_temporale, [(WARN, "BUCHI_TEMPORALI")], id="buco temporale"),
    pytest.param(lambda: sessione(session_duration_s=5.0),
                 [(WARN, "TIMER_IRREGOLARE"), (WARN, "CAMPIONI_UTILI_SCARSI")], id="troppi campioni per la durata"),
    pytest.param(lambda: sessione(SENZA_TASK_END),
                 [(ERROR, "EVENTO_RICHIESTO_ASSENTE"), (INFO, "FPS_SU_TUTTA_LA_SESSIONE")], id="TASK_END assente"),
    pytest.param(lambda: sessione(SENZA_TASK_END + [(180, "SESSION_ABORT", "F9")]),
                 [(WARN, "SESSIONE_INTERROTTA"), (WARN, "EVENTO_RICHIESTO_ASSENTE"),
                  (INFO, "FPS_SU_TUTTA_LA_SESSIONE")], id="interrotta con F9"),
    pytest.param(eventi_vuoti, [(ERROR, "EVENTI_VUOTI"), (INFO, "FPS_SU_TUTTA_LA_SESSIONE")], id="eventi vuoti"),
    pytest.param(lambda: sessione([(0, "TASK_START", ""), (50, "BARRIER_DEPART", ""), (80, "BARRIER_REACH", ""),
                                   (134, "FORK_ENTER", "left"), (200, "TASK_END", "")]),
                 [(WARN, "BARRIERA_INCOERENTE")], id="partenza prima dell'arrivo"),
    pytest.param(fps_bassi, [(WARN, "FPS_BASSI")], id="fps sotto 30"),
    pytest.param(metadati_vuoti, [(WARN, "META_VUOTI")], id="metadati vuoti"),
    pytest.param(lambda: sessione(min_path_cm=1430.0), [(ERROR, "PERCORSO_SOTTO_MINIMO")],
                 id="percorso sotto il minimo"),
    pytest.param(lambda: sessione(min_path_cm=1410.0), [], id="scarto entro la tolleranza"),
]


@pytest.mark.parametrize("crea, attesi", CASI)
def test_rilievi_del_referto(crea, attesi):
    referto = valida(crea())

    assert [(r.livello, r.codice) for r in referto.rilievi] == attesi
