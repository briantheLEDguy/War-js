#include "WarWorldEditSubsystem.h"
#include "WarPlayerController.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"
#include "HAL/FileManager.h"

namespace
{
    FString DraftPath()
    {
        if (FParse::Param(FCommandLine::Get(), TEXT("WarCapitalProof")))
        {
            static const FString ProofId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
            return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("WorldEditProof"), ProofId, TEXT("draft.json"));
        }
        return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("WorldEdit/aegis_capital-draft.json"));
    }
    bool ReadDraftFile(FString& Contents, FString& Error)
    {
        const int64 Size = IFileManager::Get().FileSize(*DraftPath());
        if (Size < 0 || Size > 2000000 || !FFileHelper::LoadFileToString(Contents, *DraftPath()))
        { Error = TEXT("No readable capital draft was found, or it exceeds the size limit."); return false; }
        return true;
    }
}

bool UWarWorldEditSubsystem::CanUse(const APlayerController* Controller) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    const UWorld* World = GetWorld();
    const auto* Player = Cast<AWarPlayerController>(Controller);
    // A client option must never grant GM access on a shared server. This local
    // workbench is deliberately separate from the still-unavailable trusted role.
    return World && World->GetNetMode() == NM_Standalone && World->IsGameWorld()
        && World->GetMapName().EndsWith(TEXT("AegisCapital_Workbench"))
        && (World->WorldType == EWorldType::PIE || FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM")))
        && Player && Player->HasAuthority() && Player->IsLocalController() && Player->GetPawn()
        && Player->GetEntryFailure().IsEmpty();
#endif
}

bool UWarWorldEditSubsystem::Open(APlayerController* Controller, FString& Error)
{
    if (!CanUse(Controller)) { Error = TEXT("GM workbench access is unavailable for this session."); return false; }
    if (!Actors.IsEmpty()) return Ready(Controller, Error);
    TArray<FWarWorldEditObject> Objects;
    TMap<FName, TWeakObjectPtr<AActor>> Candidates;
    for (TActorIterator<AStaticMeshActor> It(GetWorld()); It; ++It)
    {
        if (!It->ActorHasTag(TEXT("WarCapitalBuilding"))) continue;
        FName Id; FString SourceHash;
        for (const auto Tag : It->Tags)
            if (Tag.ToString().StartsWith(TEXT("WarWorldObject_")))
            {
                if (!Id.IsNone()) { Error = TEXT("Ambiguous authored object identity."); return false; }
                Id = FName(*Tag.ToString().RightChop(15));
            }
            else if (Tag.ToString().StartsWith(TEXT("WarModelSha256_")))
            {
                if (!SourceHash.IsEmpty()) { Error = TEXT("Ambiguous building source provenance."); return false; }
                SourceHash = Tag.ToString().RightChop(15);
            }
        if (Id.IsNone() || Candidates.Contains(Id) || SourceHash.Len() != 64 || !It->GetStaticMeshComponent()->GetStaticMesh())
        { Error = FString::Printf(TEXT("Invalid building %s: id=%s source hash length=%d mesh=%d duplicate=%d"),
            *It->GetName(), *Id.ToString(), SourceHash.Len(), It->GetStaticMeshComponent()->GetStaticMesh() != nullptr, Candidates.Contains(Id)); return false; }
        Candidates.Add(Id, *It); Objects.Add({ Id, It->GetActorTransform(), It->IsHidden(),
            It->GetStaticMeshComponent()->GetStaticMesh()->GetPathName() + TEXT(":") + SourceHash });
    }
    if (!History.Initialize(Objects, Error)) return false;
    Actors = MoveTemp(Candidates); return true;
}

AActor* UWarWorldEditSubsystem::GetObjectActor(const FName Id) const
{
    const auto* Actor = Actors.Find(Id); return Actor ? Actor->Get() : nullptr;
}

FString UWarWorldEditSubsystem::GetDraftLocation() const { return DraftPath(); }

bool UWarWorldEditSubsystem::Ready(APlayerController* Controller, FString& Error)
{
    if (!CanUse(Controller) || Actors.IsEmpty())
    { Error = TEXT("Open the authorized GM workbench before editing."); return false; }
    for (const auto& Pair : Actors)
        if (!Pair.Value.IsValid() || !Pair.Value->GetRootComponent())
        { Error = TEXT("The world changed outside the draft; reload the map before editing."); return false; }
    return true;
}

void UWarWorldEditSubsystem::ApplyActors()
{
    for (const auto& Row : History.GetObjects())
    {
        AActor* Actor = GetObjectActor(Row.Id);
        if (Actor->GetActorTransform().Equals(Row.Transform, 0.0001) && Actor->IsHidden() == Row.bHidden) continue;
        TArray<UPrimitiveComponent*> Components; Actor->GetComponents(Components);
        for (auto* Component : Components) Component->SetMobility(EComponentMobility::Movable);
        Actor->SetActorTransform(Row.Transform, false, nullptr, ETeleportType::TeleportPhysics);
        Actor->SetActorHiddenInGame(Row.bHidden);
        Actor->SetActorEnableCollision(!Row.bHidden);
    }
}

bool UWarWorldEditSubsystem::Edit(APlayerController* Controller, const FName Id, const FTransform& Transform,
    const bool bHidden, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error) || !History.Edit(Id, Transform, bHidden, Revision, Error)) return false;
    ApplyActors(); return true;
}

bool UWarWorldEditSubsystem::Undo(APlayerController* Controller, const bool bRedo, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error) || !History.Undo(bRedo, Revision, Error)) return false;
    ApplyActors(); return true;
}

bool UWarWorldEditSubsystem::SaveDraft(APlayerController* Controller, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error)) return false;
    if (Revision != History.GetRevision()) { Error = TEXT("Draft changed; refresh before saving."); return false; }
    if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(DraftPath()), true))
    { Error = TEXT("Could not create the draft directory."); return false; }
    const FString LockPath = DraftPath() + TEXT(".lock");
    TUniquePtr<FArchive> Lock(IFileManager::Get().CreateFileWriter(*LockPath, FILEWRITE_NoReplaceExisting));
    if (!Lock) { Error = TEXT("Another draft save holds the lock. Current edits remain in memory."); return false; }
    ON_SCOPE_EXIT { Lock.Reset(); IFileManager::Get().Delete(*LockPath); };
    if (IFileManager::Get().FileExists(*DraftPath()))
    {
        FString CurrentDisk;
        if (!ReadDraftFile(CurrentDisk, Error)) return false;
        if (!bObservedDisk || CurrentDisk != LastDiskContents)
        { Error = TEXT("A saved draft exists or changed elsewhere. Load it before saving; unsaved edits remain in undo history."); return false; }
    }
    else if (bObservedDisk && !LastDiskContents.IsEmpty())
    { Error = TEXT("The saved draft was removed outside this session; reload before saving."); return false; }
    const FString Json = History.ExportDraft();
    const FString Temporary = DraftPath() + TEXT(".") + FGuid::NewGuid().ToString(EGuidFormats::Digits) + TEXT(".tmp");
    if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(DraftPath()), true)
        || !FFileHelper::SaveStringToFile(Json, *Temporary, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        || !IFileManager::Get().Move(*DraftPath(), *Temporary, true, false))
    {
        IFileManager::Get().Delete(*Temporary);
        Error = TEXT("Could not save the draft. Your current edits are still in memory."); return false;
    }
    LastDiskContents = Json; bObservedDisk = true; return true;
}

bool UWarWorldEditSubsystem::LoadDraft(APlayerController* Controller, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error)) return false;
    FString Json;
    if (!ReadDraftFile(Json, Error) || !History.ImportDraft(Json, Revision, Error)) return false;
    LastDiskContents = Json; bObservedDisk = true; ApplyActors(); return true;
}
