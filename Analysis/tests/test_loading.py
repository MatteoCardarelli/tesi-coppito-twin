"""Test della lettura dei file (loading.py)"""

import pandas as pd

from coppito_analysis.loading import carica_sessione, deduplica_timestamp, leggi_eventi, leggi_stream, trova_sessioni
from tests.sintetici import crea_sessione, rettilineo, scrivi_sessione

INTESTAZIONE_EVENTI = "t,event,value,pos_x,pos_y,pos_z\n"

def test_una_cella_value_vuota_resta_stringa_vuota(tmp_path):
    percorso = tmp_path / "P01_events.csv"
    percorso.write_text(INTESTAZIONE_EVENTI + "1.0,TASK_START,,0,0,98.1\n", encoding="utf-8")

    assert leggi_eventi(percorso)["value"].tolist() == [""]

def test_un_ramo_con_nome_numerico_resta_testo(tmp_path):
    percorso = tmp_path / "P01_events.csv"
    percorso.write_text(INTESTAZIONE_EVENTI + "1.0,FORK_ENTER,1,0,0,98.1\n", encoding="utf-8")

    assert leggi_eventi(percorso)["value"].tolist() == ["1"]

def test_un_valore_illeggibile_diventa_nan(tmp_path):
    percorso = tmp_path / "P01_stream.csv"
    percorso.write_text("t,pos_x,pos_y\n0.0,abc,0.0\n0.05,7.0,0.0\n", encoding="utf-8")

    assert leggi_stream(percorso)["pos_x"].isna().tolist() == [True, False]

def test_la_deduplica_tiene_la_prima_riga():
    stream = pd.DataFrame({"t": [0.0, 0.0, 0.05], "pos_x": [1.0, 2.0, 3.0]})

    assert deduplica_timestamp(stream)["pos_x"].tolist() == [1.0, 3.0]

def test_l_id_di_sessione_e_il_nome_dello_stream_senza_suffisso(tmp_path):
    (tmp_path / "P03_2026-09-10_1530_stream.csv").write_text("t\n")
    (tmp_path / "P09_meta.json").write_text("{}")

    assert trova_sessioni(tmp_path) == ["P03_2026-09-10_1530"]

def test_metadati_corrotti_non_fermano_il_caricamento(tmp_path):
    scrivi_sessione(tmp_path, crea_sessione(*rettilineo(10.0), session_id="P01"))
    (tmp_path / "P01_meta.json").write_text('{"sampling_hz": 20', encoding="utf-8")

    sessione = carica_sessione(tmp_path, "P01")

    assert [r.codice for r in sessione.referto.rilievi] == ["META_ILLEGGIBILE"]
