"""Pipeline di analisi dei log comportamentali di CoppitoTwin (capitolo 6).

Le metriche della tesi non sono scritte nei log: si derivano qui
(logging-design.md §5). Moduli del §6.2, in ordine di dipendenza:

    sessione     strutture dati e schemi condivisi da tutta la pipeline
    validazione  controlli di qualità che compilano il referto
    loading      lettura dei tre file di una sessione e deduplica
"""
