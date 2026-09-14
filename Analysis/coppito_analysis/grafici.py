"""Grafici delle traiettorie

Ogni funzione restituisce una Figure senza salvarla: nome e formato del file
li sceglie chi la chiama.
"""

from matplotlib.figure import Figure

from .inversioni import intervalli_di_inversione
from .sessione import Sessione

# evento: (marcatore, etichetta in legenda)
EVENTI_DA_SEGNARE = {
    "TASK_START": ("o", "inizio"),
    "BARRIER_REACH": ("s", "arrivo alla barriera"),
    "BARRIER_DEPART": ("D", "ripartenza dalla barriera"),
    "FORK_ENTER": ("^", "ingresso nel bivio"),
    "TASK_END": ("X", "fine"),
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