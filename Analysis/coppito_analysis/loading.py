"""Lettura dei tre file di una sessione e assemblaggio della Sessione (cap. 6.2).

Principio: la lettura non prende decisioni, marca. Le funzioni `leggi_*` non
scartano, non riordinano e non correggono nulla: i valori illeggibili diventano
NaN e restano visibili a `validazione`, che li conta. L'unico giudizio espresso
qui è su ciò che rende una sessione impossibile da assemblare.
"""

import json
from pathlib import Path

import pandas as pd

from .sessione import (
    COLONNE_EVENTI_ESSENZIALI,
    COLONNE_EVENTI_NUMERICHE,
    COLONNE_EVENTI_TESTO,
    COLONNE_STREAM,
    COLONNE_STREAM_ESSENZIALI,
    ERROR,
    WARN,
    Referto,
    Sessione,
)

SUFFISSO_STREAM = "_stream.csv"
SUFFISSO_EVENTI = "_events.csv"
SUFFISSO_META = "_meta.json"


def leggi_stream(percorso: str | Path) -> pd.DataFrame:
    """Legge un file *_stream.csv"""

    df = pd.read_csv(percorso, encoding="utf-8-sig")

    for colonna in COLONNE_STREAM:
        if colonna in df.columns:
            df[colonna] = pd.to_numeric(df[colonna], errors="coerce")

    return df

def leggi_eventi(percorso: str | Path) -> pd.DataFrame:
    """Legge un file *_events.csv"""

    df = pd.read_csv(
        percorso,
        encoding="utf-8-sig",
        keep_default_na=False,
        dtype={colonna: "string" for colonna in COLONNE_EVENTI_TESTO},
    )

    for colonna in COLONNE_EVENTI_NUMERICHE:
        if colonna in df.columns:
            df[colonna] = pd.to_numeric(df[colonna], errors="coerce")

    for colonna in COLONNE_EVENTI_TESTO:
        if colonna in df.columns:
            df[colonna] = df[colonna].str.strip()

    return df

def leggi_meta(percorso: str | Path) -> dict:
    """Legge un file *_meta.json"""

    return json.loads(Path(percorso).read_text(encoding="utf-8-sig"))

def deduplica_timestamp(stream: pd.DataFrame) -> pd.DataFrame:
    """Elimina i campioni che condividono il timestamp con uno precedente"""

    return stream.drop_duplicates(subset="t", keep="first").reset_index(drop=True)

def trova_sessioni(cartella: str | Path) -> list[str]:
    """Gli id delle sessioni presenti in una cartella, in ordine alfabetico"""

    percorsi = Path(cartella).glob(f"*{SUFFISSO_STREAM}")
    return sorted(p.name.removesuffix(SUFFISSO_STREAM) for p in percorsi)

def _eventi_vuoti() -> pd.DataFrame:
    """Una tabella eventi con le colonne attese e nessuna riga"""

    return pd.DataFrame(columns=list(COLONNE_EVENTI_NUMERICHE + COLONNE_EVENTI_TESTO))

def carica_sessione(cartella: str | Path, session_id: str) -> Sessione:
    """Assembla una Sessione dai tre file"""

    cartella = Path(cartella)
    referto = Referto(session_id)

    percorso_stream = cartella / f"{session_id}{SUFFISSO_STREAM}"
    if not percorso_stream.exists():
        raise FileNotFoundError(f"stream non trovato: {percorso_stream}")
    grezzo = leggi_stream(percorso_stream)

    mancanti = [c for c in COLONNE_STREAM_ESSENZIALI if c not in grezzo.columns]
    if mancanti:
        raise ValueError(
            f"{percorso_stream.name} non analizzabile: "
            f"mancano le colonne {', '.join(mancanti)}"
        )

    percorso_eventi = cartella / f"{session_id}{SUFFISSO_EVENTI}"
    if percorso_eventi.exists():
        eventi = leggi_eventi(percorso_eventi)
        mancanti = [c for c in COLONNE_EVENTI_ESSENZIALI if c not in eventi.columns]
        if mancanti:
            eventi = _eventi_vuoti()
            referto.aggiungi(
                ERROR,
                "EVENTI_MALFORMATI",
                f"{percorso_eventi.name} senza le colonne {', '.join(mancanti)}: "
                "file ignorato, nessuna metrica puntuale calcolabile",
            )
    else:
        eventi = _eventi_vuoti()
        referto.aggiungi(
            ERROR,
            "EVENTI_ASSENTI",
            f"{percorso_eventi.name} non trovato: nessuna metrica puntuale calcolabile",
        )

    percorso_meta = cartella / f"{session_id}{SUFFISSO_META}"
    if percorso_meta.exists():
        try:
            meta = leggi_meta(percorso_meta)
        except json.JSONDecodeError as errore:
            meta = {}
            referto.aggiungi(
                WARN,
                "META_ILLEGGIBILE",
                f"{percorso_meta.name} non è JSON valido ({errore}): "
                "si usano i valori di progetto",
            )
    else:
        meta = {}
        referto.aggiungi(
            WARN,
            "META_ASSENTE",
            f"{percorso_meta.name} non trovato: si usano i valori di progetto",
        )

    return Sessione(
        session_id=session_id,
        meta=meta,
        stream_raw=grezzo,
        stream=deduplica_timestamp(grezzo),
        eventi=eventi,
        referto=referto,
    )

