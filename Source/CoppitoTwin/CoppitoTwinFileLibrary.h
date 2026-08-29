#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "CoppitoTwinFileLibrary.generated.h"

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
};