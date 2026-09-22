#include "WarWorldEditSubsystem.h"
#include "WarWorldEditMap.h"
#include "WarGmRules.h"
#include "WarRuntimeSettings.h"
#include "Misc/ConfigCacheIni.h"
#include "WarPlayerController.h"
#include "GameFramework/Pawn.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/BoxComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"
#include "HAL/FileManager.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"

namespace
{
    FString DraftPath(const UWorld* World)
    {
        const bool bPortalProof = FParse::Param(FCommandLine::Get(), TEXT("WarPortalProof"));
        if (bPortalProof || FParse::Param(FCommandLine::Get(), TEXT("WarCapitalProof")))
        {
            static const FString ProofId = [] {
                FString Requested; FGuid Guid;
                return FParse::Value(FCommandLine::Get(), TEXT("WarProofDraftId="), Requested)
                    && FGuid::ParseExact(Requested, EGuidFormats::Digits, Guid)
                    ? Guid.ToString(EGuidFormats::Digits) : FGuid::NewGuid().ToString(EGuidFormats::Digits);
            }();
            return FPaths::Combine(FPaths::ProjectSavedDir(), bPortalProof ? TEXT("WorldEditPortalProof") : TEXT("WorldEditProof"), ProofId, TEXT("draft.json"));
        }
        const bool bCrownward = World && World->GetOutermost()->GetName().Contains(TEXT("/crownward/"));
        return FPaths::Combine(FPaths::ProjectSavedDir(), bCrownward
            ? TEXT("WorldEdit/crownward-draft.json") : TEXT("WorldEdit/aegis_capital-draft.json"));
    }
    bool ReadDraftFile(const UWorld* World, FString& Contents, FString& Error)
    {
        const int64 Size = IFileManager::Get().FileSize(*DraftPath(World));
        if (Size < 0 || Size > 8000000 || !FFileHelper::LoadFileToString(Contents, *DraftPath(World)))
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
    FString SelectedMap;
    GConfig->GetString(TEXT("/Script/EngineSettings.GameMapsSettings"), TEXT("GameDefaultMap"), SelectedMap, GEngineIni);
    // A client option must never grant GM access on a shared server. This local
    // workbench is deliberately separate from the still-unavailable trusted role.
    return World && WarGmRules::AllowsDevelopmentSession(UE_BUILD_SHIPPING != 0,
        World->GetNetMode(), World->WorldType, GetDefault<UWarRuntimeSettings>()->bEnableLocalDevelopmentGM,
        FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM")))
        && WarWorldEditMap::IsSupported(UWorld::RemovePIEPrefix(World->GetOutermost()->GetName()), SelectedMap)
        && Player && Player->HasAuthority() && Player->IsLocalController() && Player->GetPawn()
        && Player->GetEntryFailure().IsEmpty();
#endif
}

bool UWarWorldEditSubsystem::Open(APlayerController* Controller, FString& Error)
{
    if (!CanUse(Controller)) { Error = TEXT("GM workbench access is unavailable for this session."); return false; }
    if (bInitialized) return Ready(Controller, Error);
    TArray<FWarWorldEditObject> Objects;
    TMap<FName, TWeakObjectPtr<AActor>> Candidates;
    TMap<FName, FModelTemplate> CandidateTemplates;
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
        FModelTemplate Template; Template.Mesh = It->GetStaticMeshComponent()->GetStaticMesh();
        Template.LevelPackage = It->GetLevel()->GetOutermost()->GetFName();
        const auto* MeshComponent = It->GetStaticMeshComponent();
        if (MeshComponent->GetCollisionEnabled() != ECollisionEnabled::NoCollision)
        {
            const auto* Body = Template.Mesh->GetBodySetup();
            // Licensed modular meshes retain their authored convex collision;
            // a bounding box would seal doors and destroy interior traversal.
            if (!Body || (Body->AggGeom.GetElementCount() == 0 && Body->CollisionTraceFlag != CTF_UseComplexAsSimple)
                || MeshComponent->GetCollisionProfileName() != TEXT("BlockAll"))
            { Error = TEXT("The building requires reviewed authored mesh collision."); return false; }
            Template.MeshCollisionProfile = TEXT("BlockAll");
        }
        for (int32 Index = 0; Index < MeshComponent->GetNumMaterials(); ++Index)
            Template.Materials.Add(MeshComponent->GetMaterial(Index));
        TArray<UBoxComponent*> Boxes; It->GetComponents(Boxes);
        for (const auto* Box : Boxes)
            Template.Collision.Add({ Box->GetRelativeTransform(), Box->GetUnscaledBoxExtent(), Box->GetCollisionProfileName(), Box->GetFName() });
        if (Template.Collision.IsEmpty() && Template.MeshCollisionProfile == TEXT("NoCollision"))
        { Error = TEXT("The building template has no authored collision."); return false; }
        CandidateTemplates.Add(Id, MoveTemp(Template));
    }
    if (!History.Initialize(Objects, Error)) return false;
    Actors = MoveTemp(Candidates); Templates = MoveTemp(CandidateTemplates);
    for (const auto& Pair : Templates) BaselineLevels.Add(Pair.Key, Pair.Value.LevelPackage);
    LevelAddedHandle = FWorldDelegates::LevelAddedToWorld.AddUObject(this, &ThisClass::LevelAdded);
    LevelRemovedHandle = FWorldDelegates::LevelRemovedFromWorld.AddUObject(this, &ThisClass::LevelRemoved);
    bInitialized = true; return true;
}

AActor* UWarWorldEditSubsystem::GetObjectActor(const FName Id) const
{
    const auto* Actor = Actors.Find(Id); return Actor ? Actor->Get() : nullptr;
}

FString UWarWorldEditSubsystem::GetDraftLocation() const { return DraftPath(GetWorld()); }

FName UWarWorldEditSubsystem::PickObject(const APlayerController* Controller, const FVector Origin, const FVector Direction) const
{
    if (!CanUse(Controller) || Origin.ContainsNaN() || Direction.ContainsNaN() || !Direction.IsNormalized()) return NAME_None;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WarEditorSelection), true);
    Query.AddIgnoredActor(Controller->GetPawn());
    // First blocking surface wins: never select a building through terrain or another object.
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Origin, Origin + Direction * 100000, ECC_Visibility, Query)) return NAME_None;
    for (const auto& Pair : Actors)
    {
        if (!Pair.Value.IsValid() || Pair.Value.Get() != Hit.GetActor()) continue;
        const auto* Row = History.Find(Pair.Key);
        return Row && !Row->bHidden ? Pair.Key : NAME_None;
    }
    return NAME_None;
}

bool UWarWorldEditSubsystem::Ready(APlayerController* Controller, FString& Error)
{
    if (!CanUse(Controller) || !bInitialized)
    { Error = TEXT("Open the authorized GM workbench before editing."); return false; }
    if (!StreamingConflict.IsEmpty()) { Error = StreamingConflict; return false; }
    for (const auto& Pair : Actors)
        if ((!Pair.Value.IsValid() || !Pair.Value->GetRootComponent())
            && BaselineLevels.Contains(Pair.Key) && LoadedLevel(BaselineLevels[Pair.Key]))
        { Error = TEXT("The world changed outside the draft; reload the map before editing."); return false; }
    return true;
}

void UWarWorldEditSubsystem::ApplyActors()
{
    for (const auto& Pair : Actors)
    {
        AActor* Actor = Pair.Value.Get();
        if (!IsValid(Actor)) continue; // The document and undo stacks outlive streamed actors.
        const auto* Found = History.Find(Pair.Key);
        if (!Found) { Actor->SetActorHiddenInGame(true); Actor->SetActorEnableCollision(false); continue; }
        const auto& Row = *Found;
        if (Actor->GetActorTransform().Equals(Row.Transform, 0.0001) && Actor->IsHidden() == Row.bHidden) continue;
        TArray<UPrimitiveComponent*> Components; Actor->GetComponents(Components);
        for (auto* Component : Components) Component->SetMobility(EComponentMobility::Movable);
        Actor->SetActorTransform(Row.Transform, false, nullptr, ETeleportType::TeleportPhysics);
        Actor->SetActorHiddenInGame(Row.bHidden);
        Actor->SetActorEnableCollision(!Row.bHidden);
    }
}

bool UWarWorldEditSubsystem::ApplyHistory(FWarWorldEditHistory Next, FString& Error)
{
    // Stage all new actors before committing history. Drafts select trusted model
    // templates; they cannot supply asset paths or collision geometry.
    TMap<FName, TWeakObjectPtr<AActor>> Staged;
    bool bCommitted = false;
    ON_SCOPE_EXIT { if (!bCommitted) for (const auto& Pair : Staged) if (Pair.Value.IsValid()) Pair.Value->Destroy(); };
    for (const auto& Row : Next.GetObjects())
    {
        if (const auto* Existing = Actors.Find(Row.Id); Existing && Existing->IsValid()) continue;
        if (Row.TemplateId.IsNone()) continue; // Authored actors return from their original level, never a substitute.
        const auto* Template = Templates.Find(Row.TemplateId);
        if (!Template) { Error = TEXT("Required authored model is unavailable; the draft was not applied."); return false; }
        ULevel* Level = LoadedLevel(Template->LevelPackage);
        if (!Level) continue;
        UStaticMesh* Model = Template->Mesh.LoadSynchronous();
        if (!Model) { Error = TEXT("Required authored model is unavailable; the draft was not applied."); return false; }
        TArray<UMaterialInterface*> Materials;
        for (const auto& Ref : Template->Materials)
        {
            auto* Material = Ref.LoadSynchronous();
            if (!Ref.IsNull() && !Material) { Error = TEXT("Required authored material is unavailable; the draft was not applied."); return false; }
            Materials.Add(Material);
        }
        FActorSpawnParameters Params; Params.OverrideLevel = Level;
        auto* Actor = GetWorld()->SpawnActor<AStaticMeshActor>(Params);
        if (!Actor) { Error = TEXT("Could not create the building; the draft was not applied."); return false; }
        Staged.Add(Row.Id, Actor);
        Actor->SetActorHiddenInGame(true); Actor->SetActorEnableCollision(false);
        auto* Mesh = Actor->GetStaticMeshComponent(); Mesh->SetMobility(EComponentMobility::Movable);
        Mesh->SetStaticMesh(Model); Mesh->SetCollisionProfileName(Template->MeshCollisionProfile);
        for (int32 Index = 0; Index < Template->Materials.Num(); ++Index)
            Mesh->SetMaterial(Index, Materials[Index]);
        Actor->Tags.Add(TEXT("WarCreatedBuilding")); Actor->Tags.Add(FName(*(TEXT("WarWorldObject_") + Row.Id.ToString())));
        for (const auto& Collision : Template->Collision)
        {
            auto* Box = NewObject<UBoxComponent>(Actor, Collision.Name);
            if (!Box) { Error = TEXT("Could not create authored collision; the draft was not applied."); return false; }
            Actor->AddInstanceComponent(Box); Box->SetupAttachment(Mesh); Box->SetMobility(EComponentMobility::Movable);
            Box->SetBoxExtent(Collision.Extent); Box->SetRelativeTransform(Collision.Transform);
            Box->SetCollisionProfileName(Collision.Profile); Box->SetHiddenInGame(true); Box->RegisterComponent();
        }
    }
    Actors.Append(Staged); History = MoveTemp(Next); ApplyActors(); bCommitted = true;
    // Undo may remove a created object. Destroy it now and recreate it from its
    // immutable template on redo, keeping actor memory bounded by the document.
    for (auto It = Actors.CreateIterator(); It; ++It)
        if (!History.Find(It.Key())) { if (It.Value().IsValid()) It.Value()->Destroy(); It.RemoveCurrent(); }
    return true;
}

bool UWarWorldEditSubsystem::Create(APlayerController* Controller, const FName TemplateId, const FTransform& Transform,
    const int32 Revision, FName& CreatedId, FString& Error)
{
    CreatedId = NAME_None;
    if (!Ready(Controller, Error)) return false;
    auto Next = History;
    const FName Id(*(TEXT("gm_") + FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    if (!Next.Create(Id, TemplateId, Transform, Revision, Error) || !ApplyHistory(MoveTemp(Next), Error)) return false;
    CreatedId = Id; return true;
}

bool UWarWorldEditSubsystem::Edit(APlayerController* Controller, const FName Id, const FTransform& Transform,
    const bool bHidden, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error) || !History.Edit(Id, Transform, bHidden, Revision, Error)) return false;
    ApplyActors(); return true;
}

bool UWarWorldEditSubsystem::Undo(APlayerController* Controller, const bool bRedo, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error)) return false;
    auto Next = History;
    return Next.Undo(bRedo, Revision, Error) && ApplyHistory(MoveTemp(Next), Error);
}

bool UWarWorldEditSubsystem::SaveDraft(APlayerController* Controller, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error)) return false;
    if (Revision != History.GetRevision()) { Error = TEXT("Draft changed; refresh before saving."); return false; }
    if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(DraftPath(GetWorld())), true))
    { Error = TEXT("Could not create the draft directory."); return false; }
    const FString LockPath = DraftPath(GetWorld()) + TEXT(".lock");
    TUniquePtr<FArchive> Lock(IFileManager::Get().CreateFileWriter(*LockPath, FILEWRITE_NoReplaceExisting));
    if (!Lock) { Error = TEXT("Another draft save holds the lock. Current edits remain in memory."); return false; }
    ON_SCOPE_EXIT { Lock.Reset(); IFileManager::Get().Delete(*LockPath); };
    if (IFileManager::Get().FileExists(*DraftPath(GetWorld())))
    {
        FString CurrentDisk;
        if (!ReadDraftFile(GetWorld(), CurrentDisk, Error)) return false;
        if (!bObservedDisk || CurrentDisk != LastDiskContents)
        { Error = TEXT("A saved draft exists or changed elsewhere. Load it before saving; unsaved edits remain in undo history."); return false; }
    }
    else if (bObservedDisk && !LastDiskContents.IsEmpty())
    { Error = TEXT("The saved draft was removed outside this session; reload before saving."); return false; }
    const FString Json = History.ExportDraft();
    // Never replace a readable draft with a document the loader would reject.
    if (FTCHARToUTF8(*Json).Length() > 8000000)
    { Error = TEXT("This city draft exceeds the 8 MB limit. Current edits remain in memory."); return false; }
    const FString Temporary = DraftPath(GetWorld()) + TEXT(".") + FGuid::NewGuid().ToString(EGuidFormats::Digits) + TEXT(".tmp");
    if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(DraftPath(GetWorld())), true)
        || !FFileHelper::SaveStringToFile(Json, *Temporary, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        || !IFileManager::Get().Move(*DraftPath(GetWorld()), *Temporary, true, false))
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
    auto Next = History;
    if (!ReadDraftFile(GetWorld(), Json, Error) || !Next.ImportDraft(Json, Revision, Error) || !ApplyHistory(MoveTemp(Next), Error)) return false;
    LastDiskContents = Json; bObservedDisk = true; return true;
}

bool UWarWorldEditSubsystem::ResetDraft(APlayerController* Controller, int32 Revision, FString& Error)
{
    if (!Ready(Controller,Error)) return false;
    auto Next=History;
    return Next.Reset(Revision,Error) && ApplyHistory(MoveTemp(Next),Error);
}
bool UWarWorldEditSubsystem::Duplicate(APlayerController* Controller,FName Id,int32 Revision,FName& CreatedId,FString& Error)
{
    if (!Ready(Controller,Error)) return false;
    const auto* Row=History.Find(Id);
    if (!Row || Row->bHidden) { Error=TEXT("Select a visible model to duplicate."); return false; }
    FTransform Transform=Row->Transform;
    Transform.AddToTranslation(FVector(0,200,0));
    return Create(Controller,Row->TemplateId.IsNone() ? Row->Id : Row->TemplateId,Transform,Revision,CreatedId,Error);
}
