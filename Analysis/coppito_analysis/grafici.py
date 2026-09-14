"""Grafici delle traiettorie

Ogni funzione restituisce una Figure senza salvarla: nome e formato del file
li sceglie chi la chiama.
"""

from matplotlib.figure import Figure

from .inversioni import intervalli_di_inversione
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
