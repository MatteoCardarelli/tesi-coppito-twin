"""Controlli di qualità sulle sessioni caricate"""

from .sessione import (
    COLONNE_EVENTI_NUMERICHE,
    COLONNE_EVENTI_TESTO,
    COLONNE_STREAM,
    ERROR,
    INFO,
    WARN,
    Referto,
    Sessione,
)

TOLLERANZA_INTEGRITA = 0.05    # soglia di progetto, da tarare sui dati del pilot
FATTORE_BUCO = 2.0             # intervallo oltre il doppio del nominale = campione perso
FPS_SOGLIA_BASSA = 30.0        # sotto: navigazione meno fluida, il comportamento ne risente
FPS_QUOTA_SEGNALABILE = 0.01   # sotto l'1% dei campioni è un episodio isolato

EVENTI_RICHIESTI = ("TASK_START", "TASK_END")
COPPIA_BARRIERA = ("BARRIER_REACH", "BARRIER_DEPART")
CAMPI_META_UTILI = ("barrier_pos", "fork_pos")


def _eventi_inutilizzabili(sessione: Sessione) -> bool:
    """Vero se `carica_sessione` ha già dichiarato inutilizzabile il file eventi"""

    return (sessione.referto.contiene("EVENTI_ASSENTI")
            or sessione.referto.contiene("EVENTI_MALFORMATI"))


def controlla_colonne(sessione: Sessione) -> None:
    """Verifica che i file abbiano le colonne attese e valori leggibili"""

    tabelle = (
        ("stream", sessione.stream_raw, COLONNE_STREAM, COLONNE_STREAM),
        ("eventi", sessione.eventi, COLONNE_EVENTI_NUMERICHE + COLONNE_EVENTI_TESTO,
         COLONNE_EVENTI_NUMERICHE),
    )

    for nome, tabella, attese, numeriche in tabelle:
        mancanti = [colonna for colonna in attese if colonna not in tabella.columns]
        if mancanti:
            sessione.referto.aggiungi(
                WARN,
                "COLONNE_MANCANTI",
                f"{nome}: mancano le colonne {', '.join(mancanti)}",
            )

        illeggibili = []
        for colonna in numeriche:
            if colonna in tabella.columns:
                quanti = int(tabella[colonna].isna().sum())
                if quanti:
                    illeggibili.append(f"{colonna} ({quanti})")
        if illeggibili:
            sessione.referto.aggiungi(
                WARN,
                "VALORI_ILLEGGIBILI",
                f"{nome}: valori non numerici diventati NaN in lettura: "
                f"{', '.join(illeggibili)}",
            )


def controlla_duplicati(sessione: Sessione) -> None:
    """Verifica che le righe con lo stesso timestamp fossero lo stesso istante"""

    grezzo = sessione.stream_raw
    timestamp_distinti = len(grezzo.drop_duplicates(subset="t"))
    righe_distinte = len(grezzo.drop_duplicates())
    scartate = len(grezzo) - timestamp_distinti

    if scartate == 0:
        return

    sessione.referto.aggiungi(
        INFO,
        "DEDUPLICA",
        f"{scartate} righe su {len(grezzo)} avevano un timestamp già visto",
    )

    incoerenti = righe_distinte - timestamp_distinti
    if incoerenti > 0:
        sessione.referto.aggiungi(
            WARN,
            "DUPLICATI_INCOERENTI",
            f"{incoerenti} delle righe scartate differivano per qualcosa oltre al "
            "timestamp: non erano lo stesso istante ripetuto, e la deduplica ha "
            "perso dati reali",
        )


def controlla_conteggi(sessione: Sessione) -> None:
    """Confronta i conteggi dichiarati nei metadati con i record reali"""
    confronti = [("stream_rows", len(sessione.stream_raw))]
    if not _eventi_inutilizzabili(sessione):
        confronti.append(("event_rows", len(sessione.eventi)))

    for chiave, reali in confronti:
        dichiarati = sessione.meta.get(chiave)
        if dichiarati is None:
            continue

        scarto = int(dichiarati) - reali
        if scarto == 0:
            continue

        if scarto == 1:
            sessione.referto.aggiungi(
                WARN,
                "CONTEGGIO_HEADER",
                f"{chiave} dichiara {dichiarati} contro {reali} record reali: "
                "è il difetto noto dell'intestazione conteggiata",
            )
        else:
            sessione.referto.aggiungi(
                ERROR,
                "CONTEGGIO_DIVERGENTE",
                f"{chiave} dichiara {dichiarati} contro {reali} record reali: "
                f"scarto di {scarto}, non spiegabile con l'intestazione",
            )


def controlla_tempo(sessione: Sessione) -> None:
    """Verifica che i timestamp siano crescenti e senza interruzioni"""

    stream = sessione.stream
    if stream.empty:
        sessione.referto.aggiungi(ERROR, "STREAM_VUOTO", "nessun campione nello stream")
        return

    if not stream["t"].is_monotonic_increasing:
        sessione.referto.aggiungi(
            WARN,
            "TEMPO_NON_MONOTONO",
            "i timestamp dello stream non sono crescenti: le metriche basate su "
            "differenze fra righe consecutive non sono affidabili",
        )

    if not sessione.eventi.empty and not sessione.eventi["t"].is_monotonic_increasing:
        sessione.referto.aggiungi(
            WARN,
            "EVENTI_NON_MONOTONI",
            "gli eventi non sono in ordine temporale: il primo evento di un tipo "
            "non coincide con il più antico",
        )

    if sessione.sampling_hz <= 0:
        return   # frequenza non dichiarata: già segnalata da controlla_integrita

    nominale = 1.0 / sessione.sampling_hz
    intervalli = stream["t"].diff().iloc[1:]
    buchi = intervalli[intervalli > FATTORE_BUCO * nominale]

    if not buchi.empty:
        sessione.referto.aggiungi(
            WARN,
            "BUCHI_TEMPORALI",
            f"{len(buchi)} intervalli oltre {FATTORE_BUCO:.0f}x il nominale "
            f"({nominale * 1000:.0f} ms): il più lungo {buchi.max():.3f} s, "
            f"{buchi.sum():.3f} s complessivi senza campioni",
        )


def controlla_integrita(sessione: Sessione) -> None:
    """Verifica che il numero di campioni sia compatibile con la frequenza"""

    if sessione.stream_raw.empty:
        return   # già segnalato da controlla_tempo come STREAM_VUOTO

    durata = sessione.durata_s
    attesa = sessione.sampling_hz

    if durata <= 0 or attesa <= 0:
        sessione.referto.aggiungi(
            WARN,
            "INTEGRITA_NON_VERIFICABILE",
            f"durata {durata} s e frequenza {attesa} Hz: controllo saltato",
        )
        return

    misure = (
        ("TIMER_IRREGOLARE", len(sessione.stream_raw),
         "scatti del timer al secondo: ha perso colpi, esaminare la colonna fps"),
        ("CAMPIONI_UTILI_SCARSI", len(sessione.stream),
         "campioni indipendenti al secondo dopo la deduplica"),
    )

    for codice, righe, spiegazione in misure:
        misurata = righe / durata
        scarto = abs(misurata - attesa) / attesa
        if scarto > TOLLERANZA_INTEGRITA:
            sessione.referto.aggiungi(
                WARN,
                codice,
                f"{misurata:.2f} {spiegazione} "
                f"(attesi {attesa:.1f} Hz, scarto {scarto:.1%})",
            )


def controlla_eventi(sessione: Sessione) -> None:
    """Verifica che gli eventi necessari alle metriche puntuali ci siano"""

    if sessione.eventi.empty:
        if not _eventi_inutilizzabili(sessione):
            sessione.referto.aggiungi(
                ERROR,
                "EVENTI_VUOTI",
                "il file degli eventi non contiene alcun evento: nessuna metrica "
                "puntuale calcolabile",
            )
        return

    abort = sessione.primo_evento("SESSION_ABORT")
    if abort is not None:
        motivo = abort.get("value", "") or "senza motivo indicato"
        sessione.referto.aggiungi(
            WARN,
            "SESSIONE_INTERROTTA",
            f"interrotta a t={abort['t']:.3f} s ({motivo}): i dati sono parziali",
        )

    livello = WARN if abort is not None else ERROR
    for nome in EVENTI_RICHIESTI:
        if sessione.evento(nome).empty:
            sessione.referto.aggiungi(
                livello,
                "EVENTO_RICHIESTO_ASSENTE",
                f"{nome} assente: travel time e finestra del compito non calcolabili",
            )

    mancanti = [nome for nome in COPPIA_BARRIERA if sessione.evento(nome).empty]
    if mancanti:
        sessione.referto.aggiungi(
            WARN,
            "BARRIERA_INCOMPLETA",
            f"manca {' e '.join(mancanti)}: l'esitazione al blocco non è calcolabile",
        )

    if sessione.evento("FORK_ENTER").empty:
        sessione.referto.aggiungi(
            WARN,
            "FORK_ASSENTE",
            "nessun FORK_ENTER: l'alternativa scelta non è determinabile",
        )


def controlla_fps(sessione: Sessione) -> None:
    """Sorveglia il frame rate"""

    campioni = sessione.stream_compito
    if campioni is None:
        campioni = sessione.stream
        sessione.referto.aggiungi(
            INFO,
            "FPS_SU_TUTTA_LA_SESSIONE",
            "compito non delimitabile: le statistiche sul frame rate includono il "
            "caricamento del livello e non sono confrontabili con le altre sessioni",
        )

    if "fps" not in campioni.columns:
        return   # colonna assente: già segnalata da controlla_colonne

    fps = campioni["fps"].dropna()
    if fps.empty:
        return

    soglie = (
        ("FPS_SOTTO_CAMPIONAMENTO", sessione.sampling_hz,
         "il timer non poteva rispettare la cadenza: è la causa dei timestamp ripetuti"),
        ("FPS_BASSI", FPS_SOGLIA_BASSA,
         "navigazione percepibilmente meno fluida"),
    )

    for codice, soglia, spiegazione in soglie:
        quota = float((fps < soglia).mean())
        if quota > FPS_QUOTA_SEGNALABILE:
            sessione.referto.aggiungi(
                WARN,
                codice,
                f"{quota:.1%} dei campioni sotto {soglia:.0f} fps "
                f"(minimo {fps.min():.1f}): {spiegazione}",
            )


def controlla_metadati(sessione: Sessione) -> None:
    """Annota ciò che i metadati non dichiarano e che serve alle metriche"""

    if not sessione.meta:
        gia_segnalato = (sessione.referto.contiene("META_ASSENTE")
                         or sessione.referto.contiene("META_ILLEGGIBILE"))
        if not gia_segnalato:
            sessione.referto.aggiungi(
                WARN,
                "META_VUOTI",
                "i metadati non contengono alcun campo: si usano i valori di progetto",
            )
        return

    if sessione.min_path_cm is None:
        sessione.referto.aggiungi(
            INFO,
            "MIN_PATH_NON_MISURATO",
            "min_path_cm non misurato sul modello: PAO e optimal walking speed non "
            "sono calcolabili per questa sessione",
        )

    risoluzione = sessione.meta.get("screen_resolution")
    if risoluzione:
        sessione.referto.aggiungi(
            INFO,
            "RISOLUZIONE",
            f"eseguita a {risoluzione}: confrontabile solo con sessioni alla stessa "
            "risoluzione (confondente 3, distanza di prima visibilità della barriera)",
        )

    assenti = [campo for campo in CAMPI_META_UTILI if campo not in sessione.meta]
    if assenti:
        sessione.referto.aggiungi(
            WARN,
            "META_INCOMPLETI",
            f"{', '.join(assenti)} non nei metadati: la zona di deliberazione non è "
            "ridefinibile a posteriori",
        )


CONTROLLI = (
    controlla_colonne,
    controlla_duplicati,
    controlla_conteggi,
    controlla_tempo,
    controlla_integrita,
    controlla_eventi,
    controlla_fps,
    controlla_metadati,
)


def valida(sessione: Sessione) -> Referto:
    """Esegue tutti i controlli sulla sessione e restituisce il suo referto"""
    
    for controllo in CONTROLLI:
        controllo(sessione)
    return sessione.referto
