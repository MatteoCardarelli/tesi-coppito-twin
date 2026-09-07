#include "CoppitoTwinFileLibrary.h"

#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/EngineVersion.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"

FString UCoppitoTwinFileLibrary::GetLogDirectory()
{
	return FPaths::ProjectSavedDir() / TEXT("BehaviourLogs");
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

	const FString Json = FString::Printf(TEXT(
		"{\n"
		"  \"participant_id\": \"%s\",\n"
		"  \"condition\": \"%s\",\n"
		"  \"barrier_config\": \"%s\",\n"
		"  \"timestamp_utc\": \"%s\",\n"
		"  \"sampling_hz\": %.1f,\n"
		"  \"session_duration_s\": %.3f,\n"
		"  \"stream_rows\": %d,\n"
		"  \"event_rows\": %d,\n"
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
		*Condition,
		*BarrierConfig,
		*FDateTime::UtcNow().ToIso8601(),
		SamplingHz,
		SessionDurationSec,
		StreamRows,
		EventRows,
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