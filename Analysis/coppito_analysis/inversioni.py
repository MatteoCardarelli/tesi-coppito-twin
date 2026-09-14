"""Inversioni di marcia (U-turn) ricavate dallo stream"""

import numpy as np
import pandas as pd

from .sessione import Sessione

VELOCITA_MINIMA_CMS = 20.0   # sotto: la direzione di un passo è rumore; da tarare sul pilot
SOGLIA_INVERSIONE_GRADI = 135.0   # Kalantari et al. 2023; da tarare sul pilot
FINESTRA_INVERSIONE_S = 2.0       # a 140 cm/s ≈ U larga 2,5 m; da tarare sulla larghezza dei corridoi

def passi_di_marcia(sessione: Sessione) -> pd.DataFrame | None:
    """Direzione e velocità di ogni passo del compito, senza filtri"""

    campioni = sessione.stream_compito
    if campioni is None:
        return None

    punti = campioni[["t", "pos_x", "pos_y"]].dropna()
    if len(punti) < 2:
        return None

    passi = punti.diff().iloc[1:]
    velocita = np.hypot(passi["pos_x"], passi["pos_y"]) / passi["t"]
    direzione = np.degrees(np.arctan2(passi["pos_y"], passi["pos_x"]))

    return pd.DataFrame({
        "t": punti["t"].iloc[1:],
        "direzione_gradi": direzione,
        "velocita_cms": velocita,
    }).reset_index(drop=True)

def direzioni_di_marcia(sessione: Sessione) -> pd.DataFrame | None:
    """I passi del compito abbastanza veloci da avere una direzione di marcia"""

    passi = passi_di_marcia(sessione)
    if passi is None:
        return None
    return passi.loc[passi["velocita_cms"] >= VELOCITA_MINIMA_CMS].reset_index(drop=True)

def intervalli_di_inversione(sessione: Sessione) -> list[tuple[float, float]] | None:
    """Gli intervalli di tempo in cui il partecipante ha invertito la marcia"""

    direzioni = direzioni_di_marcia(sessione)
    if direzioni is None:
        return None

    t = direzioni["t"].to_numpy()
    direzione = direzioni["direzione_gradi"].to_numpy()
    fine = np.searchsorted(t, t + FINESTRA_INVERSIONE_S)

    intervalli = []
    libero_da = -np.inf
    for i in range(len(t)):
        if fine[i] >= len(t):
            break
        if t[i] < libero_da:
            continue
        rotazione = (direzione[fine[i]] - direzione[i] + 180) % 360 - 180
        if abs(rotazione) > SOGLIA_INVERSIONE_GRADI:
            intervalli.append((float(t[i]), float(t[fine[i]])))
            libero_da = t[fine[i]]

    return intervalli

def ritorni_sui_passi(sessione: Sessione) -> int | None:
    """Numero di inversioni di marcia durante il compito"""

    intervalli = intervalli_di_inversione(sessione)
    if intervalli is None:
        return None

    return len(intervalli)

