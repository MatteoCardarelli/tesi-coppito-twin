#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "CoppitoTwinFileLibrary.generated.h"

class UCharacterMovementComponent;

/**
 * Scrittura di file di testo esposta ai Blueprint.
 * Unreal non offre un nodo nativo per farlo (verificato su UE 5.8): questa
 * libreria colma quella lacuna ed è l'unico C++ del progetto.
 */
UCLASS()
class COPPITOTWIN_API UCoppitoTwinFileLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Scrive Content in Saved/BehaviourLogs/FileName.
	 * @param bAppend  false = sovrascrive, true = accoda.
	 * @return true se la scrittura e' riuscita. VA SEMPRE CONTROLLATO.
	 */
	UFUNCTION(BlueprintCallable, Category = "CoppitoTwin|File")
	static bool SaveStringToFile(const FString& Content, const FString& FileName, bool bAppend = false);

	/** Percorso della cartella dei log comportamentali. */
	UFUNCTION(BlueprintPure, Category = "CoppitoTwin|File")
	static FString GetLogDirectory();

	/**
	 * Identificativo univoco di sessione: <ParticipantID>_<AAAA-MM-GG>_<hhmmss>, ora UTC.
	 * Non e' Pure di proposito: legge l'orologio, e un nodo Pure verrebbe rivalutato
	 * a ogni collegamento, dando istanti diversi. Va chiamato una volta e salvato.
	*/
	UFUNCTION(BlueprintCallable, Category = "CoppitoTwin|File")
	static FString MakeSessionId(const FString& ParticipantID);

	/** Compone una riga dello STREAM log. Precisione fissa, separatore decimale sempre '.'. */
	UFUNCTION(BlueprintPure, Category = "CoppitoTwin|File")
	static FString MakeStreamRow(float T, FVector Position, float Yaw, float Pitch, float Speed, float Fps);

	/** Compone una riga dell'EVENT log. Value non deve contenere virgole. */
	UFUNCTION(BlueprintPure, Category = "CoppitoTwin|File")
	static FString MakeEventRow(float T, const FString& EventName, const FString& Value, FVector Position);

	/** Unisce le righe con un a capo e le scrive su file. Restituisce false se la scrittura fallisce. */
	UFUNCTION(BlueprintCallable, Category = "CoppitoTwin|File")
	static bool SaveLinesToFile(const TArray<FString>& Lines, const FString& FileName);

	/**
	 * Scrive i metadati di sessione in JSON.
	* I parametri di movimento sono letti dal componente passato, così non possono
	* divergere dalla configurazione reale del pawn. Dal mondo dello stesso componente
	* si leggono il nome del livello e le posizioni degli attori con tag "Barrier" e
	* "Fork" (uno per tag; se manca o è ripetuto il campo non viene scritto).
	* session_id è FileName senza il suffisso "_meta.json".
	*/
	UFUNCTION(BlueprintCallable, Category = "CoppitoTwin|File")
	static bool SaveSessionMetadata(
		UCharacterMovementComponent* Movement,
		const FString& ParticipantID,
		const FString& Condition,
		const FString& BarrierConfig,
		float SamplingHz,
		float MinPathCm,
		float SessionDurationSec,
		int32 StreamRows,
		int32 EventRows,
		const FString& FileName);
};