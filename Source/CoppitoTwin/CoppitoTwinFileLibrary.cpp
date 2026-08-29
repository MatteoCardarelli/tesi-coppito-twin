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