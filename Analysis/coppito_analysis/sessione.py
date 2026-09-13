"""Strutture dati condivise da tutta la pipeline"""

from dataclasses import dataclass, field

import pandas as pd

INFO = "INFO"
WARN = "WARN"
ERROR = "ERROR"

SAMPLING_HZ_ATTESO = 20.0   # logging-design.md §3; vale solo se il metadato tace

# Schema dei file prodotti dal logger (logging-design.md §3 e §4).
COLONNE_STREAM = (
    "t",
    "pos_x",
    "pos_y",
    "pos_z",
    "cam_yaw",
    "cam_pitch",
    "speed",
    "fps",
)
COLONNE_EVENTI_NUMERICHE = ("t", "pos_x", "pos_y", "pos_z")
COLONNE_EVENTI_TESTO = ("event", "value")

# Senza queste colonne un file non è analizzabile affatto.
COLONNE_STREAM_ESSENZIALI = ("t", "pos_x", "pos_y")
COLONNE_EVENTI_ESSENZIALI = ("t", "event")


@dataclass(frozen=True)
class Rilievo:
    """Un singolo problema constatato su una sessione"""

    livello: str
    codice: str
    messaggio: str

    def __str__(self) -> str:
        return f"[{self.livello:<5}] {self.codice}: {self.messaggio}"

@dataclass
class Referto:
    """L'esito della validazione di una sessione"""

    session_id: str
    rilievi: list[Rilievo] = field(default_factory=list)

    def aggiungi(self, livello: str, codice: str, messaggio: str) -> None:
        self.rilievi.append(Rilievo(livello, codice, messaggio))

    def per_livello(self, livello: str) -> list[Rilievo]:
        return [r for r in self.rilievi if r.livello == livello]

    def contiene(self, codice: str) -> bool:
        """Vero se il referto ha già un rilievo con questo codice"""

        return any(r.codice == codice for r in self.rilievi)

    @property
    def ha_errori(self) -> bool:
        return bool(self.per_livello(ERROR))

    def testo(self) -> str:
        if not self.rilievi:
            return "  nessun rilievo"
        return "\n".join(f"  {r}" for r in self.rilievi)

@dataclass
class Sessione:
    """Una sessione caricata: i dati grezzi, quelli puliti e il referto"""

    session_id: str
    meta: dict
    stream_raw: pd.DataFrame
    stream: pd.DataFrame
    eventi: pd.DataFrame
    referto: Referto

    @property
    def participant_id(self) -> str:
        """Codice del partecipante, cercato sotto entrambe le convenzioni"""

        for chiave in ("participant_id", "participant_code"):
            if chiave in self.meta:
                return str(self.meta[chiave])
        return self.session_id

    @property
    def min_path_cm(self) -> float | None:
        """Percorso minimo praticabile da X a Y, o None se non ancora misurato"""
        valore = self.meta.get("min_path_cm")
        if valore is None or float(valore) <= 0.0:
            return None
        return float(valore)

    @property
    def sampling_hz(self) -> float:
        """Frequenza di campionamento dichiarata nei metadati"""

        valore = self.meta.get("sampling_hz")
        if valore is None:
            return SAMPLING_HZ_ATTESO
        return float(valore)

    @property
    def durata_s(self) -> float:
        """Durata della sessione come dichiarata dal logger"""

        dichiarata = self.meta.get("session_duration_s")
        if dichiarata is not None:
            return float(dichiarata)
        if self.stream.empty:
            return 0.0
        return float(self.stream["t"].iloc[-1] - self.stream["t"].iloc[0])

    @property
    def stream_compito(self) -> pd.DataFrame | None:
        """I campioni compresi fra TASK_START e TASK_END, o None se non delimitabili"""

        inizio = self.primo_evento("TASK_START")
        fine = self.primo_evento("TASK_END")
        if inizio is None or fine is None:
            return None

        t = self.stream["t"]
        return self.stream.loc[(t >= inizio["t"]) & (t <= fine["t"])]

    def evento(self, nome: str) -> pd.DataFrame:
        """Tutte le occorrenze di un evento, nell'ordine in cui compaiono"""

        if self.eventi.empty:
            return self.eventi
        return self.eventi.loc[self.eventi["event"] == nome]

    def primo_evento(self, nome: str) -> pd.Series | None:
        """La prima occorrenza di un evento, o None se non ce n'è nessuna"""
        
        righe = self.evento(nome)
        if righe.empty:
            return None
        return righe.iloc[0]
