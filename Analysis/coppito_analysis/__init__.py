"""Pipeline di analisi dei log comportamentali di CoppitoTwin (capitolo 6).

Le metriche della tesi non sono scritte nei log: si derivano qui, in ordine di dipendenza:

    sessione     strutture dati e schemi condivisi da tutta la pipeline
    validazione  controlli di qualità che compilano il referto
    loading      lettura dei tre file di una sessione e deduplica
"""
