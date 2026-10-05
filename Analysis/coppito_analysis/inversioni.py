"""Inversioni di marcia (U-turn) ricavate dallo stream"""

import numpy as np
import pandas as pd

from .sessione import Sessione

VELOCITA_MINIMA_CMS = 20.0   # sotto: la direzione di un passo è rumore; da tarare sul pilot
SOGLIA_INVERSIONE_GRADI = 135.0   # Kalantari et al. 2023; da tarare sul pilot
FINESTRA_INVERSIONE_S = 2.0       # a 140 cm/s ≈ U larga 2,5 m; da tarare sulla larghezza dei corridoi
VELOCITA_VERTICALE_MINIMA_CMS = 10.0   # sopra: il passo cambia quota (scala, rampa); in piano vale 0
PAUSA_IN_SCALA_S = 5.0            # passi in quota più vicini di così: stesso tratto, pianerottolo compreso
DISLIVELLO_MINIMO_SCALA_CM = 100.0   # sotto: gradini e terrazze (fino a 50 cm), non una scala; primo pianerottolo a 120 cm

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

def tratti_in_quota(sessione: Sessione) -> list[tuple[float, float]] | None:
    """Gli intervalli del compito passati a cambiare quota: rampe e pianerottoli fra di esse

    In pianta il pianerottolo di una scala a rampe è un giro di 180°: senza questi
    intervalli ogni salita conterebbe un'inversione di marcia mai avvenuta.
    Un tratto conta solo se il dislivello complessivo è di almeno
    DISLIVELLO_MINIMO_SCALA_CM: due gradini non sono una scala, e un dietrofront
    subito dopo, come davanti alla barriera sul basamento, va contato.
    Si uniscono solo passi nello stesso verso: una scala si sale o si scende. Senza
    questa regola la discesa dal basamento e i gradini del pavimento, a pochi
    secondi dalla scala vera, le si attaccavano e ne prendevano il dislivello.
    """

    campioni = sessione.stream_compito
    if campioni is None:
        return None

    punti = campioni[["t", "pos_z"]].dropna()
    if len(punti) < 2:
        return []

    passi = punti.diff().iloc[1:]
    in_quota = (passi["pos_z"].abs() / passi["t"]) >= VELOCITA_VERTICALE_MINIMA_CMS
    fine_passo = punti["t"].iloc[1:][in_quota].to_numpy()
    inizio_passo = punti["t"].iloc[:-1][in_quota.to_numpy()].to_numpy()
    verso_passo = np.sign(passi["pos_z"][in_quota]).to_numpy()   # +1 sale, -1 scende

    tratti: list[tuple[float, float, float]] = []   # inizio, fine, verso
    for inizio, fine, verso in zip(inizio_passo, fine_passo, verso_passo):
        if tratti and verso == tratti[-1][2] and inizio - tratti[-1][1] <= PAUSA_IN_SCALA_S:
            tratti[-1] = (tratti[-1][0], float(fine), verso)
        else:
            tratti.append((float(inizio), float(fine), verso))

    quote = punti.set_index("t")["pos_z"]
    return [(inizio, fine) for inizio, fine, _ in tratti
            if quote.loc[inizio:fine].max() - quote.loc[inizio:fine].min() >= DISLIVELLO_MINIMO_SCALA_CM]

def intervalli_di_inversione(sessione: Sessione) -> list[tuple[float, float]] | None:
    """Gli intervalli di tempo in cui il partecipante ha invertito la marcia, fuori dalle scale"""

    direzioni = direzioni_di_marcia(sessione)
    if direzioni is None:
        return None
    in_quota = tratti_in_quota(sessione) or []

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
            if any(da <= t[fine[i]] and t[i] <= a for da, a in in_quota):
                continue
            intervalli.append((float(t[i]), float(t[fine[i]])))
            libero_da = t[fine[i]]

    return intervalli

def ritorni_sui_passi(sessione: Sessione) -> int | None:
    """Numero di inversioni di marcia durante il compito"""

    intervalli = intervalli_di_inversione(sessione)
    if intervalli is None:
        return None

    return len(intervalli)

