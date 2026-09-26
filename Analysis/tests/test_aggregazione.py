"""Test dell'aggregazione dello studio e dell'export (aggregazione.py)"""

import pytest

import coppito_analysis.aggregazione as aggregazione
import coppito_analysis.validazione as validazione
from coppito_analysis.aggregazione import (
    analizza_studio,
    carica_tutte,
    controlla_alternative,
    controlla_configurazione,
    controlla_partecipanti,
    esporta,
    tabella_sessioni,
)
from coppito_analysis.sessione import Referto
from coppito_analysis.validazione import valida
from tests.sintetici import crea_sessione, rettilineo, scrivi_sessione

def sessione(session_id="P01", ramo="left", con_fine=True, **meta):
    """Sessione validata; senza TASK_END non è utilizzabile"""

    t, x, y = rettilineo(10.0)
    eventi = [(t[0], "TASK_START", ""), (t[134], "FORK_ENTER", ramo)]
    if con_fine:
        eventi.append((t[200], "TASK_END", ""))
    risultato = crea_sessione(t, x, y, eventi=eventi, session_id=session_id, **meta)
    valida(risultato)
    return risultato

def codici(referto):
    return [r.codice for r in referto.rilievi]

def test_una_sessione_non_caricabile_non_ferma_lo_studio(tmp_path):
    scrivi_sessione(tmp_path, sessione("P01"))
    rotta = sessione("P02")
    rotta.stream_raw = rotta.stream_raw.drop(columns="t")
    scrivi_sessione(tmp_path, rotta)

    sessioni, studio = carica_tutte(tmp_path)

    assert [s.session_id for s in sessioni] == ["P01"]
    assert codici(studio) == ["SESSIONE_NON_CARICABILE"]

def test_una_sessione_senza_stream_viene_segnalata_e_non_sparisce(tmp_path):
    scrivi_sessione(tmp_path, sessione("P01"))
    (tmp_path / "P01_stream.csv").unlink()

    sessioni, studio = carica_tutte(tmp_path)

    assert sessioni == []
    assert codici(studio) == ["SESSIONE_NON_CARICABILE"]
    assert "stream non trovato" in studio.rilievi[0].messaggio

def test_un_difetto_del_codice_ferma_l_analisi(tmp_path, monkeypatch):
    scrivi_sessione(tmp_path, sessione("P01"))

    def controllo_difettoso(sessione):
        raise ValueError("difetto in un controllo")

    monkeypatch.setattr(validazione, "CONTROLLI", validazione.CONTROLLI + (controllo_difettoso,))
    with pytest.raises(ValueError):
        carica_tutte(tmp_path)

    def lettura_difettosa(cartella, session_id):
        raise KeyError("difetto nella lettura")

    monkeypatch.setattr(aggregazione, "carica_sessione", lettura_difettosa)
    with pytest.raises(KeyError):
        carica_tutte(tmp_path)

def test_i_ritorni_sui_passi_restano_interi_nel_csv():
    tabella = tabella_sessioni([sessione("P01"), sessione("P02", con_fine=False)])

    assert tabella["ritorni_sui_passi"].to_csv(index=False).split() == ["ritorni_sui_passi", "0", '""']

def test_una_risoluzione_non_dichiarata_conta_come_configurazione_diversa():
    tabella = tabella_sessioni([sessione("P01", screen_resolution="1920x1080"), sessione("P02")])
    studio = Referto("STUDIO")

    controlla_configurazione(tabella, studio)

    assert codici(studio) == ["CONFIGURAZIONE_DIVERSA"]

def test_un_partecipante_in_due_sessioni_viene_segnalato():
    tabella = tabella_sessioni([sessione("P01_a", participant_id="P01"), sessione("P01_b", participant_id="P01")])
    studio = Referto("STUDIO")

    controlla_partecipanti(tabella, studio)

    assert codici(studio) == ["PARTECIPANTE_RIPETUTO"]

def test_lo_stesso_ramo_scritto_in_due_modi_viene_segnalato():
    tabella = tabella_sessioni([sessione("P01", ramo="left"), sessione("P02", ramo="Left")])
    studio = Referto("STUDIO")

    controlla_alternative(tabella, studio)

    assert codici(studio) == ["ALTERNATIVE_OSSERVATE", "ALTERNATIVE_INCOERENTI"]

def test_l_analisi_esegue_i_controlli_fra_sessioni_e_l_export_scrive_il_bom(tmp_path):
    scrivi_sessione(tmp_path, sessione("P01_a", participant_id="P01", screen_resolution="1920x1080"))
    scrivi_sessione(tmp_path, sessione("P01_b", participant_id="P01"))

    sessioni, rilievi = analizza_studio(tmp_path)
    percorso_sessioni, _ = esporta(sessioni, rilievi, tmp_path / "output")

    assert rilievi.loc[rilievi["session_id"] == "STUDIO", "codice"].tolist() == [
        "CONFIGURAZIONE_DIVERSA", "PARTECIPANTE_RIPETUTO", "ALTERNATIVE_OSSERVATE"]
    assert percorso_sessioni.read_bytes()[:3] == b"\xef\xbb\xbf"

def test_esportare_uno_studio_vuoto_rimuove_il_vecchio_sessioni_csv(tmp_path):
    scrivi_sessione(tmp_path, sessione("P01"))
    uscita = tmp_path / "output"
    esporta(*analizza_studio(tmp_path), uscita)

    esporta(*analizza_studio(tmp_path / "vuota"), uscita)

    assert not (uscita / "sessioni.csv").exists()
