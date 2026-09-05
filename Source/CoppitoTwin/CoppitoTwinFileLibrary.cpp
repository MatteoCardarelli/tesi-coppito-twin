#include "CoppitoTwinFileLibrary.h"

#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"

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