"""Test delle inversioni di marcia (inversioni.py)"""

import numpy as np
import pytest

from coppito_analysis.inversioni import ritorni_sui_passi
from tests.sintetici import crea_sessione, percorso

SCENARI = [
    pytest.param([("dritto", 4.0), ("indietro", 4.0)], 1, id="ritorno tenendo premuto S"),
    pytest.param([("dritto", 4.0), ("curva", 180.0, 0.5), ("dritto", 4.0)], 1, id="inversione in curva"),
    pytest.param([("dritto", 4.0), ("indietro", 3.0), ("indietro", 4.0)], 2, id="due inversioni"),
    pytest.param([("dritto", 4.0), ("curva", 140.0, 0.6), ("curva", -15.0, 0.3), ("curva", 55.0, 0.6),
                  ("dritto", 4.0)], 1, id="ripensamento a meta curva"),
    pytest.param([("dritto", 4.0), ("curva", 90.0, 0.7), ("dritto", 150.0 / 140.0), ("curva", 90.0, 0.7),
                  ("dritto", 4.0)], 0, id="aggiramento a U di 150 cm"),
    pytest.param([("indietro", 4.0), ("fermo", 3.0), ("dritto", 4.0)], 0, id="sosta camminando verso ovest"),
]

@pytest.mark.parametrize("tratti, attese", SCENARI)
def test_inversioni_contate(tratti, attese):
    assert ritorni_sui_passi(crea_sessione(*percorso(tratti))) == attese

RAMPA_S = 300.0 / 140.0   # rampa di 3 m in pianta, come le scale d'angolo del modello

def salita_a_due_rampe(dopo):
    """Piano, rampa, pianerottolo, rampa, poi i tratti `dopo` al piano di sopra

    Sul pianerottolo: 1 m avanti, giro stretto di 180°, 1 m avanti. Dura più della
    finestra delle inversioni, quindi una finestra può starci dentro senza toccare le rampe.
    """

    pianerottolo = [("dritto", 1.0), ("curva", 180.0, 0.5), ("dritto", 1.0)]
    tratti = [("dritto", 4.0), ("dritto", RAMPA_S)] + pianerottolo + [("dritto", RAMPA_S)] + dopo
    t, x, y = percorso(tratti)
    tappe = np.cumsum([0.0, 4.0, RAMPA_S, 2.5, RAMPA_S])
    z = np.interp(t, tappe, [0.0, 0.0, 175.0, 175.0, 350.0])
    sessione = crea_sessione(t, x, y)
    sessione.stream["pos_z"] = z
    return sessione

def test_il_pianerottolo_non_e_un_inversione():
    assert ritorni_sui_passi(salita_a_due_rampe([("dritto", 4.0)])) == 0

def test_al_piano_di_sopra_le_inversioni_si_contano_ancora():
    assert ritorni_sui_passi(salita_a_due_rampe([("dritto", 4.0), ("indietro", 4.0)])) == 1
