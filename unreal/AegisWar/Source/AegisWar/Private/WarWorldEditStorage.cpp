#include "WarWorldEditStorage.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "HAL/CriticalSection.h"
#include "Misc/SecureHash.h"
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#else
#include <cstdio>
#endif

namespace
{
    bool ReplacePublication(const FString& Path, const FString& Temporary)
    {
        // IFileManager::Move deletes the old file first; use an atomic same-directory rename.
        const FString Destination = FPaths::ConvertRelativePathToFull(Path);
        const FString Source = FPaths::ConvertRelativePathToFull(Temporary);
#if PLATFORM_WINDOWS
        return ::MoveFileExW(*Source, *Destination, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
        return std::rename(TCHAR_TO_UTF8(*Source), TCHAR_TO_UTF8(*Destination)) == 0;
#endif
    }
}

bool WarWorldEditStorage::Read(const FString& Path, FString& Contents, FString& Error)
{
    Contents.Empty();
    if (!IFileManager::Get().FileExists(*Path)) return true;
    const int64 Size = IFileManager::Get().FileSize(*Path);
    if (Size <= 0 || Size > 8000000 || !FFileHelper::LoadFileToString(Contents, *Path))
    { Error = TEXT("Published world is unreadable or exceeds 8 MB. Restore the file before retrying."); return false; }
    return true;
}

bool WarWorldEditStorage::Publish(const FString& Path, const FString& Observed, const FString& Contents, FString& Error)
{
    if (Contents.IsEmpty() || FTCHARToUTF8(*Contents).Length() > 8000000)
    { Error = TEXT("Published world must contain a document no larger than 8 MB."); return false; }
    if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path), true))
    { Error = TEXT("Could not create the local publication directory."); return false; }
    FString Canonical = FPaths::ConvertRelativePathToFull(Path); FPaths::NormalizeFilename(Canonical);
    FSystemWideCriticalSection ProcessLock(TEXT("AegisWorldPublish_") + FMD5::HashAnsiString(*Canonical.ToLower()));
    if (!ProcessLock.IsValid()) { Error = TEXT("Another publication is in progress. Retry when it finishes."); return false; }
    const FString LockPath = Path + TEXT(".lock");
    // Generic file writers do not implement NoReplaceExisting on every platform.
    if (IFileManager::Get().FileExists(*LockPath))
    { Error = TEXT("A publication lock remains. Check that no other game is publishing before removing it."); return false; }
    TUniquePtr<FArchive> Lock(IFileManager::Get().CreateFileWriter(*LockPath, FILEWRITE_NoReplaceExisting));
    if (!Lock) { Error = TEXT("Another publication holds the writer lock. Retry when it finishes."); return false; }
    ON_SCOPE_EXIT { Lock.Reset(); IFileManager::Get().Delete(*LockPath); };
    FString Current;
    if (!Read(Path, Current, Error)) return false;
    if (Current != Observed)
    { Error = TEXT("The published world changed in another session. Save your draft and restart before publishing."); return false; }
    const FString Temporary = Path + TEXT(".") + FGuid::NewGuid().ToString(EGuidFormats::Digits) + TEXT(".tmp");
    ON_SCOPE_EXIT { IFileManager::Get().Delete(*Temporary); };
    if (!FFileHelper::SaveStringToFile(Contents, *Temporary, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        || !ReplacePublication(Path, Temporary))
    { Error = TEXT("Could not publish. Previous publication and current edits are retained."); return false; }
    return true;
}
