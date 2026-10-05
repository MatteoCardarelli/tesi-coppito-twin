@echo off
rem Avvio di una sessione del pilot.
rem Gioco standalone, schermo intero a 1920x1080 per tutti i partecipanti: la risoluzione
rem cambia la distanza da cui si vede la barriera (confondente 3), quindi non deve dipendere
rem dalla finestra dell'editor. Avvio normale, senza i plugin MCP.
rem I file di sessione finiscono in Saved\BehaviourLogs, come dall'editor.
rem Il livello e' indicato qui: la mappa predefinita del gioco (DefaultEngine.ini) e' ancora
rem il prototipo Lvl_FirstPerson, e senza questo argomento la sessione partirebbe li'.

"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "%~dp0CoppitoTwin.uproject" /Game/Coppito/Maps/Lvl_Coppito_Prova -game -fullscreen -ResX=1920 -ResY=1080
