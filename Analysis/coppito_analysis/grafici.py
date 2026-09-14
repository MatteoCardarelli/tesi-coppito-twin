"""Grafici delle traiettorie

Ogni funzione restituisce una Figure senza salvarla: nome e formato del file
li sceglie chi la chiama.
"""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

from .inversioni import VELOCITA_MINIMA_CMS, direzioni_di_marcia, intervalli_di_inversione, passi_di_marcia
from .sessione import Sessione
from .metriche import alternativa_scelta


# evento: (marcatore, etichetta in legenda)
EVENTI_DA_SEGNARE = {
    "TASK_START": ("o", "inizio"),
    "BARRIER_REACH": ("s", "arrivo alla barriera"),
    "BARRIER_DEPART": ("D", "ripartenza dalla barriera"),
    "FORK_ENTER": ("^", "ingresso nel bivio"),
    "TASK_END": ("X", "fine"),
}

# ramo: (colore, tratto) - i nomi sono i value dei trigger del bivio
STILI_ALTERNATIVE = {
    "left": ("#2a78d6", "-"),
    "right": ("#eb6834", "--"),
}

def grafico_traiettoria(sessione: Sessione) -> Figure:
    """Pianta della traiettoria, con gli eventi e le inversioni di marcia"""

    campioni = sessione.stream_compito
    titolo = sessione.session_id
    if campioni is None:
        campioni = sessione.stream
        titolo += " (compito non delimitabile: sessione intera)"
    punti = campioni[["t", "pos_x", "pos_y"]].dropna()

    figura = Figure(figsize=(8, 6), layout="constrained")
    assi = figura.subplots()
    assi.plot(punti["pos_x"], punti["pos_y"], color="0.6", linewidth=1, label="traiettoria")

    for numero, (inizio, fine) in enumerate(intervalli_di_inversione(sessione) or []):
        tratto = punti.loc[punti["t"].between(inizio, fine)]
        assi.plot(tratto["pos_x"], tratto["pos_y"], color="tab:red", linewidth=3,
                  label="finestra di un'inversione di marcia" if numero == 0 else None)

    for nome, (marcatore, etichetta) in EVENTI_DA_SEGNARE.items():
        righe = sessione.evento(nome)
        if not righe.empty:
            assi.plot(righe["pos_x"], righe["pos_y"], marcatore, color="black", markersize=8, label=etichetta)

    assi.set_aspect("equal", adjustable="datalim")
    assi.invert_yaxis()
    assi.set_xlabel("x (cm)")
    assi.set_ylabel("y (cm)")
    assi.set_title(titolo)
    figura.legend(loc="outside lower center", ncols=3, fontsize="small")
    return figura

def grafico_sessioni_sovrapposte(sessioni: list[Sessione]) -> Figure:
    """Le traiettorie di tutte le sessioni in una pianta, distinte per alternativa scelta"""

    delimitabili = [s for s in sessioni if s.stream_compito is not None]

    figura = Figure(figsize=(8, 6), layout="constrained")
    assi = figura.subplots()

    for sessione in delimitabili:
        punti = sessione.stream_compito[["pos_x", "pos_y"]].dropna()
        nome = alternativa_scelta(sessione)
        if nome in STILI_ALTERNATIVE:
            colore, tratto = STILI_ALTERNATIVE[nome]
            etichetta = nome
        elif nome is None:
            colore, tratto, etichetta = "0.6", "-", "nessuna alternativa"
        else:
            colore, tratto, etichetta = "0.6", ":", "ramo con nome non previsto"
        assi.plot(punti["pos_x"], punti["pos_y"], color=colore, linestyle=tratto, linewidth=1.5, label=etichetta)

    for sessione in delimitabili:
        bivio = sessione.primo_evento("FORK_ENTER")
        if bivio is not None:
            assi.plot(bivio["pos_x"], bivio["pos_y"], "^", color="black", markersize=8, label="ingresso nel bivio")

    titolo = f"Sessioni sovrapposte: {len(delimitabili)}"
    escluse = len(sessioni) - len(delimitabili)
    if escluse:
        titolo += f" (escluse perché senza compito delimitabile: {escluse})"

    assi.set_aspect("equal", adjustable="datalim")
    assi.invert_yaxis()
    assi.set_xlabel("x (cm)")
    assi.set_ylabel("y (cm)")
    assi.set_title(titolo)
    maniglie, etichette = assi.get_legend_handles_labels()
    uniche = dict(zip(etichette, maniglie))
    if uniche:
        figura.legend(uniche.values(), uniche.keys(), loc="outside lower center", ncols=3, fontsize="small")
    return figura

def grafico_direzione_velocita(sessione: Sessione) -> Figure | None:
    """Velocità e direzione di marcia nel tempo, con la soglia di velocità e le inversioni"""

    passi = passi_di_marcia(sessione)
    if passi is None:
        return None
    direzioni = direzioni_di_marcia(sessione)

    figura = Figure(figsize=(8, 6), layout="constrained")
    assi_velocita, assi_direzione = figura.subplots(2, 1, sharex=True)

    assi_velocita.plot(passi["t"], passi["velocita_cms"], color="#2a78d6", linewidth=1.5,
                       label="velocità di ogni passo")
    assi_velocita.axhline(VELOCITA_MINIMA_CMS, color="black", linestyle="--", linewidth=1,
                          label=f"soglia di velocità ({VELOCITA_MINIMA_CMS:.0f} cm/s)")

    gradi = np.degrees(np.unwrap(np.radians(direzioni["direzione_gradi"])))
    assi_direzione.plot(direzioni["t"], gradi, ".", color="#2a78d6", markersize=4,
                        label="direzione dei passi sopra soglia")

    for numero, (inizio, fine) in enumerate(intervalli_di_inversione(sessione)):
        assi_velocita.axvspan(inizio, fine, color="tab:red", alpha=0.15,
                              label="finestra di un'inversione di marcia" if numero == 0 else None)
        assi_direzione.axvspan(inizio, fine, color="tab:red", alpha=0.15)

    assi_velocita.set_ylabel("velocità (cm/s)")
    assi_direzione.set_ylabel("direzione di marcia (°)")
    assi_direzione.yaxis.set_major_locator(MultipleLocator(90))
    assi_direzione.set_ylim(gradi.min() - 90, gradi.max() + 90)
    assi_direzione.set_xlabel("tempo dall'inizio della registrazione (s)")
    figura.suptitle(sessione.session_id)
    figura.legend(loc="outside lower center", ncols=2, fontsize="small")
    return figura