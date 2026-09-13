"""Test delle strutture dati condivise (sessione.py)"""

from coppito_analysis.sessione import WARN, Referto
from tests.sintetici import crea_sessione, rettilineo


def test_i_soli_avvisi_non_rendono_la_sessione_inutilizzabile():
    referto = Referto("P00")
    referto.aggiungi(WARN, "CONTEGGIO_HEADER", "612 dichiarate contro 611")

    assert not referto.ha_errori


def test_i_valori_dichiarati_nei_metadati_non_vengono_sostituiti():
    sessione = crea_sessione(*rettilineo(10.0), sampling_hz=0, session_duration_s=12.5)

    assert sessione.sampling_hz == 0.0
    assert sessione.durata_s == 12.5


def test_il_partecipante_si_legge_anche_da_participant_code():
    sessione = crea_sessione(*rettilineo(10.0), session_id="P03_2026-09-10_1530")
    del sessione.meta["participant_id"]
    sessione.meta["participant_code"] = "P03"

    assert sessione.participant_id == "P03"
