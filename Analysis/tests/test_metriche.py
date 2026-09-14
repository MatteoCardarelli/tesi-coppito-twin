"""Test delle metriche (metriche.py)"""

import numpy as np
import pytest

from coppito_analysis.metriche import (
    alternativa_scelta,
    esitazione_s,
    frame_rate_compito,
    lunghezza_percorso_cm,
    optimal_walking_speed_cms,
    pao_pct,
    travel_time_s,
)
from tests.sintetici import crea_sessione, rettilineo

def con_eventi(eventi, durata_s=10.0):
    """Rettilineo con gli eventi indicati per indice di campione"""

    t, x, y = rettilineo(durata_s)
    return crea_sessione(t, x, y, eventi=[(t[i], nome, valore) for i, nome, valore in eventi])

def test_la_lunghezza_e_in_2d_e_solo_dentro_il_compito():
    sessione = con_eventi([(100, "TASK_START", ""), (300, "TASK_END", "")], durata_s=15.0)
    sessione.stream["pos_z"] = 98.1 + 20.0 * sessione.stream["t"]

    assert lunghezza_percorso_cm(sessione) == pytest.approx(1400.0)

def test_una_posizione_illeggibile_non_accorcia_il_percorso():
    sessione = crea_sessione(*rettilineo(10.0))
    sessione.stream.loc[100, "pos_x"] = np.nan

    assert lunghezza_percorso_cm(sessione) == pytest.approx(1400.0)

def test_con_task_end_prima_di_task_start_non_si_calcola_nulla():
    sessione = con_eventi([(50, "TASK_END", ""), (150, "TASK_START", "")])

    assert lunghezza_percorso_cm(sessione) is None
    assert travel_time_s(sessione) is None

def test_l_esitazione_usa_la_prima_partenza_dopo_il_primo_arrivo():
    sessione = con_eventi([
        (0, "TASK_START", ""),
        (10, "BARRIER_DEPART", ""),
        (20, "BARRIER_REACH", ""),
        (60, "BARRIER_DEPART", ""),
        (100, "BARRIER_REACH", ""),
        (180, "BARRIER_DEPART", ""),
        (200, "TASK_END", ""),
    ])

    assert esitazione_s(sessione) == pytest.approx(2.0)

def test_l_alternativa_e_il_primo_ramo_scritto_com_e():
    sessione = con_eventi([(0, "TASK_START", ""), (100, "FORK_ENTER", "Left"),
                           (150, "FORK_ENTER", "right"), (200, "TASK_END", "")])

    assert alternativa_scelta(sessione) == "Left"

def test_un_ramo_senza_nome_non_e_un_alternativa():
    sessione = con_eventi([(0, "TASK_START", ""), (100, "FORK_ENTER", ""), (200, "TASK_END", "")])

    assert alternativa_scelta(sessione) is None

def test_il_pao_riproduce_l_esempio_di_kuliga():
    sessione = crea_sessione(*rettilineo(6000.0 / 140.0), min_path_cm=5000.0)

    assert pao_pct(sessione) == pytest.approx(20.0)

def test_pao_negativo_e_velocita_ottimale():
    sessione = crea_sessione(*rettilineo(10.0), min_path_cm=1500.0)

    assert pao_pct(sessione) == pytest.approx(-100.0 / 15.0)
    assert optimal_walking_speed_cms(sessione) == pytest.approx(150.0)

def test_con_percorso_minimo_a_zero_pao_e_velocita_ottimale_sono_none():
    sessione = crea_sessione(*rettilineo(10.0), min_path_cm=0.0)

    assert pao_pct(sessione) is None
    assert optimal_walking_speed_cms(sessione) is None

def test_il_frame_rate_si_misura_solo_nel_compito():
    sessione = con_eventi([(100, "TASK_START", ""), (200, "TASK_END", "")])
    sessione.stream.loc[:99, "fps"] = 5.0

    assert frame_rate_compito(sessione)["fps_minimo"] == pytest.approx(60.0)
