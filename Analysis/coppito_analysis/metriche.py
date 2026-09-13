"""Metriche della tesi, derivate da una Sessione

Quando i dati per calcolare una metrica non ci sono, la funzione
restituisce None. 
"""

from .sessione import Sessione

from .sessione import Sessione

FPS_SOGLIA_BASSA = 30.0   # sotto: navigazione meno fluida; usata anche da validazione

def travel_time_s(sessione: Sessione) -> float | None:
    """Durata del compito: TASK_END.t − TASK_START.t"""

    inizio = sessione.primo_evento("TASK_START")
    fine = sessione.primo_evento("TASK_END")
    if inizio is None or fine is None:
        return None

    durata = float(fine["t"] - inizio["t"])
    if durata <= 0:
        return None
    return durata

def esitazione_s(sessione: Sessione) -> float | None:
    """Tempo passato nella zona di deliberazione davanti alla barriera"""

    arrivo = sessione.primo_evento("BARRIER_REACH")
    if arrivo is None:
        return None

    partenze = sessione.evento("BARRIER_DEPART")
    successive = partenze.loc[partenze["t"] > arrivo["t"]]
    if successive.empty:
        return None

    return float(successive["t"].iloc[0] - arrivo["t"])

def alternativa_scelta(sessione: Sessione) -> str | None:
    """Il ramo imboccato per primo al bivio: il `value` del primo FORK_ENTER"""

    ingresso = sessione.primo_evento("FORK_ENTER")
    if ingresso is None:
        return None

    ramo = ingresso.get("value", "")
    return ramo or None

def lunghezza_percorso_cm(sessione: Sessione) -> float | None:
    """Lunghezza del percorso durante il compito: somma delle distanze fra campioni"""

    campioni = sessione.stream_compito
    if campioni is None:
        return None

    posizioni = campioni[["pos_x", "pos_y"]].dropna()
    if len(posizioni) < 2:
        return None

    passi = posizioni.diff().iloc[1:]
    return float(((passi["pos_x"] ** 2 + passi["pos_y"] ** 2) ** 0.5).sum())

def pao_pct(sessione: Sessione) -> float | None:
    """Percentage Above Optimal: di quanto il percorso supera il minimo, in %"""

    percorso = lunghezza_percorso_cm(sessione)
    minimo = sessione.min_path_cm
    if percorso is None or minimo is None:
        return None

    return (percorso - minimo) / minimo * 100

def optimal_walking_speed_cms(sessione: Sessione) -> float | None:
    """Percorso minimo diviso travel time, in cm/s"""

    minimo = sessione.min_path_cm
    tempo = travel_time_s(sessione)
    if minimo is None or tempo is None:
        return None

    return minimo / tempo

def frame_rate_compito(sessione: Sessione) -> dict[str, float] | None:
    """Frame rate durante il compito: media, minimo e quota sotto soglia"""
    
    campioni = sessione.stream_compito
    if campioni is None or "fps" not in campioni.columns:
        return None

    fps = campioni["fps"].dropna()
    if fps.empty:
        return None

    return {
        "fps_medio": float(fps.mean()),
        "fps_minimo": float(fps.min()),
        "fps_sotto_soglia_pct": float((fps < FPS_SOGLIA_BASSA).mean() * 100),
    }