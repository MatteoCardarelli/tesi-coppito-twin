"""Analisi dello studio: dai log alle tabelle e ai grafici

Uso, dalla cartella Analysis:
    python -m scripts.analizza
    python -m scripts.analizza --log <cartella dei log> --uscita <cartella dei risultati>
    python -m scripts.analizza --min-path-cm 4600   (sostituisce il minimo dei metadati)
"""

import argparse
import shutil
from pathlib import Path

from coppito_analysis.aggregazione import analizza_studio, carica_tutte, esporta
from coppito_analysis.grafici import grafico_direzione_velocita, grafico_sessioni_sovrapposte, grafico_traiettoria
from coppito_analysis.sessione import ERROR, INFO, WARN

SAVED = Path(__file__).resolve().parents[2] / "Saved"

def salva(figura, percorso):
    """Salva la figura in PNG, creando la cartella se manca"""

    percorso.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(percorso, dpi=150)

def main():
    parser = argparse.ArgumentParser(description="Analizza tutte le sessioni di una cartella di log")
    parser.add_argument("--log", type=Path, default=SAVED / "BehaviourLogs", help="cartella dei log")
    parser.add_argument("--uscita", type=Path, default=SAVED / "Analisi", help="cartella dei risultati")
    parser.add_argument(
        "--min-path-cm", type=float, default=None,
        help="percorso minimo da usare al posto di quello dei metadati, solo in memoria",
    )
    argomenti = parser.parse_args()

    tabella, rilievi = analizza_studio(argomenti.log, argomenti.min_path_cm)
    percorso_sessioni, percorso_rilievi = esporta(tabella, rilievi, argomenti.uscita)

    grafici = argomenti.uscita / "grafici"
    if grafici.exists():
        shutil.rmtree(grafici)

    sessioni, _ = carica_tutte(argomenti.log, argomenti.min_path_cm)
    for sessione in sessioni:
        salva(grafico_traiettoria(sessione), grafici / "traiettorie" / f"{sessione.session_id}.png")
        figura = grafico_direzione_velocita(sessione)
        if figura is not None:
            salva(figura, grafici / "direzione_velocita" / f"{sessione.session_id}.png")
    if sessioni:
        salva(grafico_sessioni_sovrapposte(sessioni), grafici / "sessioni_sovrapposte.png")

    utilizzabili = 0 if tabella.empty else int(tabella["utilizzabile"].sum())
    print(f"Sessioni: {len(tabella)}, utilizzabili: {utilizzabili}")
    for livello in (ERROR, WARN, INFO):
        print(f"Rilievi {livello}: {(rilievi['livello'] == livello).sum()}")
    print(f"Tabelle: {percorso_sessioni or '(nessuna sessione)'} e {percorso_rilievi}")
    print(f"Grafici: {grafici if sessioni else '(nessuno)'}")

if __name__ == "__main__":
    main()