#include "CoppitoTwinFileLibrary.h"

#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/EngineVersion.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Kismet/GameplayStatics.h"
#include "UnrealEngine.h"

FString UCoppitoTwinFileLibrary::GetLogDirectory()
{
	return FPaths::ProjectSavedDir() / TEXT("BehaviourLogs");
}

FString UCoppitoTwinFileLibrary::MakeSessionId(const FString& ParticipantID)
{
	return ParticipantID + TEXT("_") + FDateTime::UtcNow().ToString(TEXT("%Y-%m-%d_%H%M%S"));
}

bool UCoppitoTwinFileLibrary::SaveStringToFile(const FString& Content, const FString& FileName, bool bAppend)
{
	const FString Directory = GetLogDirectory();

	IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
	if (!PlatformFile.DirectoryExists(*Directory))
	{
		PlatformFile.CreateDirectoryTree(*Directory);
	}

	const FString FullPath = FPaths::Combine(Directory, FileName);

	const bool bSuccess = FFileHelper::SaveStringToFile(
		Content,
		*FullPath,
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
		&IFileManager::Get(),
		bAppend ? FILEWRITE_Append : FILEWRITE_None);

	if (!bSuccess)
	{
		UE_LOG(LogTemp, Error, TEXT("[CoppitoTwin] Scrittura FALLITA: %s"), *FullPath);

		// Avviso a schermo che resta fino alla chiusura: una scrittura fallita in silenzio ha
		// gia' prodotto un terzetto di file incoerente (diario, 25/09/2026). Chi conduce la
		// sessione deve accorgersene prima di congedare il partecipante.
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 86400.f, FColor::Red,
				FString::Printf(TEXT("SCRITTURA FALLITA: %s -- sessione da ripetere"), *FileName),
				true, FVector2D(2.f, 2.f));
		}
	}

	return bSuccess;
}

FString UCoppitoTwinFileLibrary::MakeStreamRow(float T, FVector Position, float Yaw, float Pitch, float Speed, float Fps)
{
	return FString::Printf(TEXT("%.3f,%.1f,%.1f,%.1f,%.2f,%.2f,%.1f,%.1f"),
		T, Position.X, Position.Y, Position.Z, Yaw, Pitch, Speed, Fps);
}

FString UCoppitoTwinFileLibrary::MakeEventRow(float T, const FString& EventName, const FString& Value, FVector Position)
{
	return FString::Printf(TEXT("%.3f,%s,%s,%.1f,%.1f,%.1f"),
		T, *EventName, *Value, Position.X, Position.Y, Position.Z);
}

bool UCoppitoTwinFileLibrary::SaveLinesToFile(const TArray<FString>& Lines, const FString& FileName)
{
	if (Lines.Num() == 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("[CoppitoTwin] Nessuna riga da scrivere: %s"), *FileName);
		return false;
	}

	const FString Content = FString::Join(Lines, TEXT("\n")) + TEXT("\n");
	return SaveStringToFile(Content, FileName, false);
}

namespace
{
	// Riga JSON con la posizione dell'unico attore che porta il tag. Vuota se l'attore
	// manca o non e' unico: il campo resta assente e la pipeline lo segnala (META_INCOMPLETI).
	FString PosizioneDaTag(const UWorld* World, FName Tag, const TCHAR* Campo)
	{
		TArray<AActor*> Trovati;
		if (World)
		{
			UGameplayStatics::GetAllActorsWithTag(World, Tag, Trovati);
		}
		if (Trovati.Num() != 1)
		{
			UE_LOG(LogTemp, Error, TEXT("[CoppitoTwin] %s non scritto: %d attori con tag '%s', atteso 1"),
				Campo, Trovati.Num(), *Tag.ToString());
			return FString();
		}
		const FVector P = Trovati[0]->GetActorLocation();
		return FString::Printf(TEXT("  \"%s\": [%.1f, %.1f, %.1f],\n"), Campo, P.X, P.Y, P.Z);
	}
}

bool UCoppitoTwinFileLibrary::SaveSessionMetadata(
	UCharacterMovementComponent* Movement,
	const FString& ParticipantID,
	const FString& Condition,
	const FString& BarrierConfig,
	float SamplingHz,
	float MinPathCm,
	float SessionDurationSec,
	int32 StreamRows,
	int32 EventRows,
	const FString& FileName)
{
	FString Resolution = TEXT("sconosciuta");
	if (GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport)
	{
		const FIntPoint Size = GEngine->GameViewport->Viewport->GetSizeXY();
		Resolution = FString::Printf(TEXT("%dx%d"), Size.X, Size.Y);
	}
	else if (GSystemResolution.ResX > 0 && GSystemResolution.ResY > 0)
	{
		// Chiusura della finestra (Alt+F4): il viewport non c'e' piu' quando End Play scrive
		// i metadati. Resta la risoluzione impostata dal motore, cioe' -ResX/-ResY.
		Resolution = FString::Printf(TEXT("%dx%d"), GSystemResolution.ResX, GSystemResolution.ResY);
	}

	float MaxSpeed = 0.f, MaxAccel = 0.f, Braking = 0.f;
	float BrakeFriction = 0.f, GroundFriction = 0.f;
	bool bSeparateFriction = false;

	if (Movement)
	{
		MaxSpeed = Movement->MaxWalkSpeed;
		MaxAccel = Movement->MaxAcceleration;
		Braking = Movement->BrakingDecelerationWalking;
		BrakeFriction = Movement->BrakingFriction;
		GroundFriction = Movement->GroundFriction;
		bSeparateFriction = Movement->bUseSeparateBrakingFriction;
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("[CoppitoTwin] Metadati SENZA parametri di movimento: componente nullo"));
	}

	// Il mondo si ricava dal componente di movimento: se manca, mancano anche le posizioni.
	const UWorld* World = Movement ? Movement->GetWorld() : nullptr;
	const FString LevelName = World ? UGameplayStatics::GetCurrentLevelName(World, true) : TEXT("sconosciuto");
	const FString BarrierPos = PosizioneDaTag(World, TEXT("Barrier"), TEXT("barrier_pos"));
	const FString ForkPos = PosizioneDaTag(World, TEXT("Fork"), TEXT("fork_pos"));

	// L'identificativo di sessione e' il nome del file senza il suffisso: ricavarlo qui
	// evita un pin in piu' sul nodo, e non puo' divergere dal nome dei file.
	FString SessionID = FileName;
	SessionID.RemoveFromEnd(TEXT("_meta.json"));

	const FString Json = FString::Printf(TEXT(
		"{\n"
		"  \"participant_id\": \"%s\",\n"
		"  \"session_id\": \"%s\",\n"
		"  \"condition\": \"%s\",\n"
		"  \"barrier_config\": \"%s\",\n"
		"  \"level_name\": \"%s\",\n"
		"  \"timestamp_utc\": \"%s\",\n"
		"  \"sampling_hz\": %.1f,\n"
		"  \"session_duration_s\": %.3f,\n"
		"  \"stream_rows\": %d,\n"
		"  \"event_rows\": %d,\n"
		"%s%s"
		"  \"min_path_cm\": %.1f,\n"
		"  \"max_speed_cms\": %.1f,\n"
		"  \"max_acceleration\": %.1f,\n"
		"  \"braking_deceleration\": %.1f,\n"
		"  \"use_separate_braking_friction\": %s,\n"
		"  \"braking_friction\": %.1f,\n"
		"  \"ground_friction\": %.1f,\n"
		"  \"engine_version\": \"%s\",\n"
		"  \"screen_resolution\": \"%s\",\n"
		"  \"machine\": \"%s\"\n"
		"}\n"),
		*ParticipantID,
		*SessionID,
		*Condition,
		*BarrierConfig,
		*LevelName,
		*FDateTime::UtcNow().ToIso8601(),
		SamplingHz,
		SessionDurationSec,
		StreamRows,
		EventRows,
		*BarrierPos,
		*ForkPos,
		MinPathCm,
		MaxSpeed,
		MaxAccel,
		Braking,
		bSeparateFriction ? TEXT("true") : TEXT("false"),
		BrakeFriction,
		GroundFriction,
		*FEngineVersion::Current().ToString(),
		*Resolution,
		FPlatformProcess::ComputerName());

	return SaveStringToFile(Json, FileName, false);
}