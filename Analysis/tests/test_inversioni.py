"""Test delle inversioni di marcia (inversioni.py)"""

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
