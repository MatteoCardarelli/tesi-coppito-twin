"""Caricamento e validazione delle sessioni """

from _pytest import assertion
import json
import pandas as pd
from pandas.core import generic
from pathlib import Path
from .sessione import ERROR, Referto, Sessione, WARN

COLONNE_STREAM = (
    "t", 
    "pos_x", 
    "pos_y", 
    "pos_z", 
    "cam_yaw", 
    "cam_pitch", 
    "speed", 
    "fps"
)

COLONNE_EVENTI_NUMERICHE = (
    "t", 
    "pos_x", 
    "pos_y", 
    "pos_z"
)

COLONNE_EVENTI_TESTO = (
    "event", 
    "value"
    )

def leggi_stream(percorso: Path) -> pd.DataFrame:
    """Legge un file *_stream.csv
    
    Converte in numero tutte le colonne attese: i valori illeggibili
    diventano NaN e restano visibili alla validazione, che li conterà.
    """

    df = pd.read_csv(percorso, encoding="utf-8-sig")

    for colonna in COLONNE_STREAM:
        if colonna in df.columns:
            df[colonna] = pd.to_numeric(df[colonna], errors="coerce")

    return df

def leggi_eventi (percorso: Path) -> pd.DataFrame:
    """Legge un file *_events.csv"""

    df = pd.read_csv(
        percorso,
        encoding="utf-8-sig",
        keep_default_na=False,
        dtype={colonna: "string" for colonna in COLONNE_EVENTI_TESTO}
    )

    for colonna in COLONNE_EVENTI_NUMERICHE:
        if colonna in df.columns:
            df[colonna] = pd.to_numeric(df[colonna], errors ="coerce")

    for colonna in COLONNE_EVENTI_TESTO:
        if colonna in df.columns:
            df[colonna] = df[colonna].str.strip()
    
    return df

def leggi_meta(percorso: Path) -> dict:
    """Legge un file *_meta.json

    Restituisce le chiavi così come le scrive il logger.
    """
    return json.loads(Path(percorso).read_text(encoding="utf-8-sig"))

def deduplica_timestamp(stream: pd.DataFrame) -> pd.DataFrame:
    """Elimina i campioni che condividono il timestamp con uno precedente."""

    return stream.drop_duplicates(subset="t", keep="first").reset_index(drop=True)

def carica_sessione(cartella: str | Path, session_id: str) -> Sessione:
    """Assembla una Sessione dai tre file"""
    cartella = Path(cartella)
    referto = Referto(session_id)

    percorso_stream = cartella / f"{session_id}_stream.csv"
    if not percorso_stream.exists():
        raise FileNotFoundError(f"stream non trovato: {percorso_stream}")
    grezzo = leggi_stream(percorso_stream)

    percorso_eventi = cartella / f"{session_id}_events.csv"
    if percorso_eventi.exists():
        eventi = leggi_eventi(percorso_eventi)
    else:
        eventi = pd.DataFrame(columns=list(COLONNE_EVENTI_TESTO + COLONNE_EVENTI_NUMERICHE))
        referto.aggiungi(
            ERROR,
            "EVENTI_ASSENTI",
            f"{percorso_eventi.name} non trovato: nessuna metrica puntuale calcolabile",
        )

    percorso_meta = cartella / f"{session_id}_meta.json"
    if percorso_meta.exists():
        meta = leggi_meta(percorso_meta)
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

