"""Controlli di qualità sulle sessioni caricate"""

from .sessione import ERROR, INFO, Referto, Sessione, WARN

TOLLERANZA_INTEGRITA = 0.05 #soglia di progetto, da tarare sui dati del pilot
FATTORE_BUCO = 2.0 #un intervallo oltre il doppio del nominale = campione perso
FPS_SOGLIA_BASSA = 30.0 
FPS_QUOTA_SEGNALABILE = 0.01
EVENTI_RICHIESTI = ("TASK_START", "TASK_END")
COPPIA_BARRIERA = ("BARRIER_REACH", "BARRIER_DEPART")
CAMPI_META_UTILI = ("barrier_pos", "fork_pos")

def controlla_duplicati(sessione: Sessione) -> None:
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
            f"{incoerenti} delle righe scartate differivano per qualcosa oltre al timestamp: non erano lo stesso istante ripetuto, e la duplica ha perso dati reali",
        )

def controlla_conteggi(sessione: Sessione) -> None:
    confronti = (
        ("stream_rows", len(sessione.stream_raw)),
        ("event_rows", len(sessione.eventi)),
    )

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
                f"{chiave} dichiara {dichiarati} contro {reali} record reali: è il difetto noto dell'intestazione conteggiata",
            )
        else:
            sessione.referto.aggiungi(
                ERROR,
                "CONTEGGIO_DIVERGENTE",
                f"{chiave} dichiara {dichiarati} contro {reali} record reali:"
                f"scarto di {scarto}, non spiegabile con l'intestazione",
            )

def controlla_integrita(sessione: Sessione) -> None:
    """Controlla che il numero di campioni sia compatibile con la frequenza"""

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
        misurata = righe/durata
        scarto = abs(misurata - attesa)/attesa
        if scarto > TOLLERANZA_INTEGRITA:
            sessione.referto.aggiungi(
                WARN,
                codice,
                f"{misurata:.2f} {spiegazione} "
                f"(attesi {attesa:.1f} Hz, scarto {scarto:.1%})",
            )

def controlla_tempo(sessione: Sessione) -> None:
    """Verifica che i tempi siano crescenti e senza interruzioni"""
    stream = sessione.stream
    if stream.empty:
        sessione.referto.aggiungi(ERROR, "STREAM_VUOTO", "nessun campione nello stream")
        return

    if not stream["t"].is_monotonic_increasing:
        sessione.referto.aggiungi(
            WARN,
            "TEMPO_NON_MONOTONO",
            "i timestamp dello stream non sono crescenti: le metriche basate "
            "su differenze fra righe consecutive non sono affidabili",
        )

    if not sessione.eventi.empty and not sessione.eventi["t"].is_monotonic_increasing:
        sessione.referto.aggiungi(
            WARN,
            "EVENTI_NON_MONOTONI",
            "gli eventi non sono in ordine temporale: il primo evento di un "
            "tipo non coincide con il più antico",
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

def controlla_fps(sessione: Sessione) -> None:
    """Sorveglia il frame rate"""

    campioni = sessione.stream_compito
    if campioni is None:
        campioni = sessione.stream
        sessione.referto.aggiungi(
            INFO,
            "FPS_SU_TUTTA_LA_SESSIONE",
            "compito non delimitabile: le statistiche sul frame rate includono il caricamento del livello e non sono confrontabili con le altre sessioni",
        )

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
                f"(minimo {fps.min():.1f}): {spiegazione}"
            )

def controlla_eventi(sessione: Sessione) -> None:
    """Verfica che gli eventi necessari alle metriche puntuali ci siano."""

    if sessione.eventi.empty:
        return

    abort = sessione.primo_evento("SESSION_ABORT")
    if abort is not None:
        motivo = abort["value"] or "senza motivo indicato"
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
            "nessuna FORK_ENTER: l'alternativa scelta non è determinabile",
        )

def controlla_metadati(sessione: Sessione) -> None:
    """Annota ciò che i metadati non dichiarano e che serve alle metriche"""

    if not sessione.meta:
        return

    if sessione.min_path_cm is None:
        sessione.referto.aggiungi(
            INFO,
            "MIN_PATH_NON_MISURATO",
            "min_path_cm non misurato sul modello: PAO e optimal walking speed "
            "non sono calcolabili per questa sessione",
        )

    risoluzione = sessione.meta.get("screen_resolution")
    if risoluzione:
        sessione.referto.aggiungi(
            INFO,
            "RISOLUZIONE",
            f"eseguita a {risoluzione}: confrontabile solo con sessioni alla stessa risoluzione",
        )

    assenti = [campo for campo in CAMPI_META_UTILI if campo not in sessione.meta]
    if assenti:
        sessione.referto.aggiungi(
            WARN,
            "META_INCOMPLETI",
            f"{', '.join(assenti)} non nei metadati: la zona di deliberazione non è ridefinibile a posteriori",
        )

CONTROLLI = (
    controlla_duplicati,
    controlla_conteggi,
    controlla_tempo,
    controlla_integrita,
    controlla_eventi,
    controlla_fps,
    controlla_metadati,
)

def valida(sessione: Sessione) -> Referto:
    """Esegue tutti i controlli sulla sessione e restituisce il suo referto    """
    for controllo in CONTROLLI:
        controllo(sessione)
    return sessione.referto

