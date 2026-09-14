"""Test dei grafici (grafici.py)"""

from io import BytesIO

from coppito_analysis.grafici import grafico_direzione_velocita, grafico_sessioni_sovrapposte, grafico_traiettoria
from tests.sintetici import crea_sessione, percorso

def con_ramo(ramo):
    """Dritto, svolta e dritto, con un ingresso nel bivio al campione 80"""

    t, x, y = percorso([("dritto", 4.0), ("curva", 90.0, 1.0), ("dritto", 3.0)])
    eventi = [(t[0], "TASK_START", ""), (t[80], "FORK_ENTER", ramo), (t[-1], "TASK_END", "")]
    return crea_sessione(t, x, y, eventi=eventi)

def test_i_tre_grafici_si_disegnano_su_una_sessione_con_un_inversione():
    sessione = crea_sessione(*percorso([("dritto", 4.0), ("indietro", 4.0)]))

    for figura in (grafico_traiettoria(sessione), grafico_sessioni_sovrapposte([sessione]),
                   grafico_direzione_velocita(sessione)):
        figura.savefig(BytesIO(), format="png")

def test_senza_task_end_ogni_grafico_lo_gestisce_a_modo_suo():
    t, x, y = percorso([("dritto", 4.0)])
    sessione = crea_sessione(t, x, y, eventi=[(t[0], "TASK_START", "")])

    assert "sessione intera" in grafico_traiettoria(sessione).axes[0].get_title()
    assert "escluse" in grafico_sessioni_sovrapposte([sessione]).axes[0].get_title()
    assert grafico_direzione_velocita(sessione) is None

def test_la_legenda_ha_una_voce_per_categoria():
    figura = grafico_sessioni_sovrapposte([con_ramo("left"), con_ramo("left"), con_ramo("Right")])

    voci = [testo.get_text() for testo in figura.legends[0].get_texts()]
    assert voci == ["left", "ramo con nome non previsto", "ingresso nel bivio"]