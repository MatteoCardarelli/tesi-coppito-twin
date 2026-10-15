"""Aggregazione di più sessioni ed export dei risultati (cap. 6.6)"""

from pathlib import Path
from .inversioni import ritorni_sui_passi
from .loading import carica_sessione, trova_sessioni
from .metriche import (
    alternativa_scelta,
    esitazione_s,
    frame_rate_compito,
    lunghezza_percorso_cm,
    optimal_walking_speed_cms,
    pao_pct,
    travel_time_s,
)
from .sessione import ERROR, INFO, WARN, Referto, Sessione
from .validazione import valida

import pandas as pd

CONFIGURAZIONE_COSTANTE = (   # identiche per protocollo in tutte le sessioni dello studio
    "condizione",             # da rivedere se il protocollo introduce più condizioni
    "barrier_config",
    "min_path_cm",
    "sampling_hz",
    "max_speed_cms",          # confondente 2
    "screen_resolution",      # confondente 3
    "engine_version",         # congelamento delle versioni
)

COLONNE_RILIEVI = ("session_id", "livello", "codice", "messaggio")

def sostituisci_min_path(sessione: Sessione, valore_cm: float) -> None:
    """Sostituisce in memoria il percorso minimo dei metadati, e lo dichiara nel referto"""

    originale = sessione.meta.get("min_path_cm")
    sessione.meta["min_path_cm"] = float(valore_cm)
    sessione.referto.aggiungi(
        INFO,
        "MIN_PATH_SOSTITUITO",
        f"min_path_cm {originale} nei metadati, {float(valore_cm):.1f} usato nell'analisi",
    )

def carica_tutte(
    cartella: str | Path, min_path_cm: float | None = None
) -> tuple[list[Sessione], Referto]:
    """Carica e valida tutte le sessioni di una cartella

    Con min_path_cm il percorso minimo dei metadati viene sostituito prima della
    validazione, solo in memoria: i file delle sessioni non vengono toccati.
    """
    studio = Referto("STUDIO")
    sessioni = []

    for session_id in trova_sessioni(cartella):
        try:
            sessione = carica_sessione(cartella, session_id)
        except (ValueError, OSError) as errore:
            studio.aggiungi(
                ERROR,
                "SESSIONE_NON_CARICABILE",
                f"{session_id}: {type(errore).__name__}: {errore}",
            )
            continue
        if min_path_cm is not None:
            sostituisci_min_path(sessione, min_path_cm)
        valida(sessione)
        sessioni.append(sessione)

    if not sessioni and not studio.rilievi:
        studio.aggiungi(
            WARN,
            "NESSUNA_SESSIONE",
            f"nessun file *_stream.csv in {Path(cartella).resolve()}",
        )

    return sessioni, studio

def riga_sessione(sessione: Sessione) -> dict:
    """Una sessione già validata come riga della tabella dello studio"""

    fps = frame_rate_compito(sessione)
    meta = sessione.meta

    return {
        "session_id": sessione.session_id,
        "participant_id": sessione.participant_id,
        "condizione": meta.get("condition"),
        "inizio_utc": meta.get("timestamp_utc"),
        "utilizzabile": not sessione.referto.ha_errori,
        "errori": len(sessione.referto.per_livello(ERROR)),
        "avvisi": len(sessione.referto.per_livello(WARN)),
        "travel_time_s": travel_time_s(sessione),
        "esitazione_s": esitazione_s(sessione),
        "alternativa_scelta": alternativa_scelta(sessione),
        "lunghezza_percorso_cm": lunghezza_percorso_cm(sessione),
        "pao_pct": pao_pct(sessione),
        "optimal_walking_speed_cms": optimal_walking_speed_cms(sessione),
        "ritorni_sui_passi": ritorni_sui_passi(sessione),
        "fps_medio": fps["fps_medio"] if fps else None,
        "fps_minimo": fps["fps_minimo"] if fps else None,
        "fps_sotto_soglia_pct": fps["fps_sotto_soglia_pct"] if fps else None,
        "min_path_cm": sessione.min_path_cm,
        "sampling_hz": meta.get("sampling_hz"),
        "max_speed_cms": meta.get("max_speed_cms"),
        "screen_resolution": meta.get("screen_resolution"),
        "barrier_config": meta.get("barrier_config"),
        "engine_version": meta.get("engine_version"),
    }

def tabella_sessioni(sessioni: list[Sessione]) -> pd.DataFrame:
    """Le sessioni come tabella: una riga per sessione, nell'ordine ricevuto"""

    tabella = pd.DataFrame([riga_sessione(sessione) for sessione in sessioni])
    if tabella.empty:
        return tabella

    return tabella.astype({"ritorni_sui_passi": "Int64"})

def controlla_configurazione(tabella: pd.DataFrame, studio: Referto) -> None:
    """Segnala le configurazioni che dovrebbero essere identiche e non lo sono"""

    if tabella.empty:
        return

    for colonna in CONFIGURAZIONE_COSTANTE:
        gruppi = tabella.groupby(colonna, dropna=False)["session_id"].apply(list)
        if len(gruppi) > 1:
            dettaglio = "; ".join(
                f"{'non dichiarata' if pd.isna(valore) else valore} in {', '.join(sessioni)}"
                for valore, sessioni in gruppi.items()
            )
            studio.aggiungi(
                WARN,
                "CONFIGURAZIONE_DIVERSA",
                f"{colonna} non uniforme fra le sessioni: {dettaglio}",
            )

def controlla_partecipanti(tabella: pd.DataFrame, studio: Referto) -> None:
    """Segnala i partecipanti presenti in più di una sessione"""

    if tabella.empty:
        return

    for partecipante, righe in tabella.groupby("participant_id"):
        if len(righe) > 1:
            elenco = ", ".join(
                f"{riga.session_id} ({'utilizzabile' if riga.utilizzabile else 'non utilizzabile'})"
                for riga in righe.itertuples()
            )
            studio.aggiungi(
                WARN,
                "PARTECIPANTE_RIPETUTO",
                f"{partecipante} compare in {len(righe)} sessioni: {elenco}",
            )

def controlla_alternative(tabella: pd.DataFrame, studio: Referto) -> None:
    """Descrive le alternative scelte e segnala le grafie incoerenti di uno stesso ramo"""

    if tabella.empty:
        return

    scelte = tabella[["session_id", "alternativa_scelta"]].dropna()
    if scelte.empty:
        return

    conteggi = scelte["alternativa_scelta"].value_counts()
    studio.aggiungi(
        INFO,
        "ALTERNATIVE_OSSERVATE",
        f"su {len(scelte)} sessioni con un bivio: "
        + ", ".join(f"{ramo} in {n}" for ramo, n in conteggi.items()),
    )

    normalizzate = scelte["alternativa_scelta"].str.strip().str.casefold()
    for normalizzata, righe in scelte.groupby(normalizzate):
        grafie = righe.groupby("alternativa_scelta")["session_id"].apply(list)
        if len(grafie) > 1:
            dettaglio = "; ".join(
                f"{grafia} in {', '.join(sessioni)}" for grafia, sessioni in grafie.items()
            )
            studio.aggiungi(
                WARN,
                "ALTERNATIVE_INCOERENTI",
                f"'{normalizzata}' è scritta in {len(grafie)} modi diversi: {dettaglio}",
            )

def tabella_rilievi(sessioni: list[Sessione], studio: Referto) -> pd.DataFrame:
    """Tutti i rilievi dello studio, una riga per rilievo"""

    righe = [
        (studio.session_id, rilievo.livello, rilievo.codice, rilievo.messaggio)
        for rilievo in studio.rilievi
    ]
    for sessione in sessioni:
        righe.extend(
            (sessione.session_id, rilievo.livello, rilievo.codice, rilievo.messaggio)
            for rilievo in sessione.referto.rilievi
        )

    return pd.DataFrame(righe, columns=list(COLONNE_RILIEVI))

CONTROLLI_STUDIO = (
    controlla_configurazione,
    controlla_partecipanti,
    controlla_alternative,
)

def analizza_studio(
    cartella: str | Path, min_path_cm: float | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Dalla cartella dei log alle due tabelle dello studio: sessioni e rilievi"""

    sessioni, studio = carica_tutte(cartella, min_path_cm)
    tabella = tabella_sessioni(sessioni)

    for controllo in CONTROLLI_STUDIO:
        controllo(tabella, studio)

    return tabella, tabella_rilievi(sessioni, studio)

def esporta(
    sessioni: pd.DataFrame, rilievi: pd.DataFrame, cartella_output: str | Path
) -> tuple[Path | None, Path]:
    """Scrive le due tabelle dello studio come CSV nella cartella indicata"""
    
    cartella = Path(cartella_output)
    cartella.mkdir(parents=True, exist_ok=True)
    percorso_sessioni = cartella / "sessioni.csv"
    percorso_rilievi = cartella / "rilievi.csv"

    if sessioni.columns.empty:
        percorso_sessioni.unlink(missing_ok=True)
        percorso_sessioni = None
    else:
        sessioni.to_csv(percorso_sessioni, index=False, encoding="utf-8-sig")

    rilievi.to_csv(percorso_rilievi, index=False, encoding="utf-8-sig")
    return percorso_sessioni, percorso_rilievi