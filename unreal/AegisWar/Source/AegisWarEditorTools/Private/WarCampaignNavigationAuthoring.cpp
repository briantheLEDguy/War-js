#include "WarSiegeAuthoringLibrary.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "EngineUtils.h"
#include "NavMesh/RecastNavMesh.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarCitadelSiegeProof.h"
#include "WarSiegeBattlefield.h"
#include "WarCityDefinition.h"
#include "NavigationSystem.h"
#include "NavModifierVolume.h"
#include "NavAreas/NavArea_Null.h"
#include "Engine/LevelStreaming.h"
#include "AssetCompilingManager.h"
#if WITH_RECAST
#include "Detour/DetourNavMesh.h"
#endif

bool UWarSiegeAuthoringLibrary::IsPrivateCampaignNavigationPair(const FString& CampaignPackage, const FString& OverlayPackage)
{
    const FString Prefix=TEXT("/Game/WorldRebuild/AegisCitadel_");
    const FString Suffix=TEXT("/CampaignCandidate");
    if (!CampaignPackage.StartsWith(Prefix) || !CampaignPackage.EndsWith(Suffix)) return false;
    const FString Revision=CampaignPackage.Mid(Prefix.Len(),CampaignPackage.Len()-Prefix.Len()-Suffix.Len());
    if (Revision.Len()!=12) return false;
    for (const TCHAR C:Revision)
        if (!((C>=TEXT('0') && C<=TEXT('9')) || (C>=TEXT('a') && C<=TEXT('f')))) return false;
    return OverlayPackage==Prefix+Revision+TEXT("/CampaignSiegeOverlay");
}

namespace
{
    FString TileSnapshot(const ARecastNavMesh* Data)
    {
        TArray<FNavTileRef> Tiles;Data->GetAllNavMeshTiles(Tiles);
        Tiles.Sort([](FNavTileRef A,FNavTileRef B) { return static_cast<uint64>(A)<static_cast<uint64>(B); });
        FString Result=FString::Printf(TEXT("%s|%.9g|%.9g|%d|%d"),*Data->GetConfig().Name.ToString(),
            Data->GetConfig().AgentRadius,Data->GetConfig().AgentHeight,Data->GetNavMeshTilesCount(),Data->GetNumActiveTiles());
        int32 Populated=0;
        for (const auto Ref:Tiles)
        {
#if WITH_RECAST
            const auto* Mesh=Data->GetRecastMesh();const auto* Tile=Mesh ? Mesh->getTileByRef(static_cast<dtTileRef>(Ref)) : nullptr;
            FString Hash,Error;
            // GetAllNavMeshTiles includes allocated pool slots without a baked payload.
            if (Tile && !Tile->header && !Tile->data && Tile->dataSize==0) continue;
            if (!Tile || !Tile->header || Tile->dataSize<=0
                || !WarCitadelProofHash::Bytes(Tile->data,Tile->dataSize,Hash,Error)) return FString();
            ++Populated;
            const FBox Box=Data->GetNavMeshTileBounds(Ref);
            Result+=FString::Printf(TEXT("|%llu:%s:%s:%s"),static_cast<unsigned long long>(Ref),*Box.Min.ToString(),*Box.Max.ToString(),*Hash);
#else
            return FString();
#endif
        }
        return Populated==Data->GetNumActiveTiles() ? Result : FString();
    }
}

FString UWarSiegeAuthoringLibrary::DescribeBakedNavigation(UWorld* World)
{
    if (!World || World->IsGameWorld()) return TEXT("An editor world is required for baked data inspection");
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (TActorIterator<ARecastNavMesh> It(World);It;++It)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("actor"),It->GetPathName());
        Row->SetStringField(TEXT("package"),It->GetLevel()->GetOutermost()->GetName());
        Row->SetStringField(TEXT("profile"),It->GetConfig().Name.ToString());
        Row->SetNumberField(TEXT("activeTiles"),It->GetNumActiveTiles());
        Row->SetNumberField(TEXT("tileCapacity"),It->GetNavMeshTilesCount());
        Row->SetBoolField(TEXT("registered"),It->IsRegistered());
        Row->SetBoolField(TEXT("needsRebuild"),It->NeedsRebuild());
        Row->SetBoolField(TEXT("needsRebuildOnLoad"),It->NeedsRebuildOnLoad());
        Row->SetStringField(TEXT("tileSnapshot"),TileSnapshot(*It));
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("actors"),Rows);
    FString Result;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Result));return Result;
}

FString UWarSiegeAuthoringLibrary::RebuildCampaignNavigation(UWorld* World,const FString& OverlayPackage,
    const FString& CityRevision,const TArray<FString>& ExpectedAttachments,const TArray<FString>& ExpectedLoadedPackages)
{
    const auto Fail=[](const TCHAR* Reason)
    { UE_LOG(LogTemp,Warning,TEXT("WAR_CAMPAIGN_NAV_REBUILD_BLOCKED %s"),Reason);return FString(Reason); };
    if (!IsInGameThread() || !World || World->IsGameWorld() || !World->PersistentLevel
        || World->GetCurrentLevel()!=World->PersistentLevel
        || !IsPrivateCampaignNavigationPair(World->GetOutermost()->GetName(),OverlayPackage))
        return Fail(TEXT("Only the matching private campaign editor world may rebuild navigation"));
    const FString CampaignPackage=World->GetOutermost()->GetName();
    const FString Root=CampaignPackage.LeftChop(FString(TEXT("CampaignCandidate")).Len());
    if (CityRevision.Len()!=64) return Fail(TEXT("The exact shared scenery revision is required"));
    for (const TCHAR C:CityRevision)
        if (!((C>=TEXT('0') && C<=TEXT('9')) || (C>=TEXT('a') && C<=TEXT('f'))))
            return Fail(TEXT("The shared scenery revision must be a SHA-256 identity"));
    TSet<FString> Expected,LoadedExpected;
    for (const FString& Package:ExpectedAttachments)
    {
        if (!Package.StartsWith(TEXT("/Game/")) || Expected.Contains(Package) || Package==CampaignPackage)
            return Fail(TEXT("Attachment inventory must contain distinct Game packages"));
        Expected.Add(Package);
    }
    for (const FString& Package:ExpectedLoadedPackages)
    {
        if (!Expected.Contains(Package) || LoadedExpected.Contains(Package))
            return Fail(TEXT("Loaded packages must be a distinct subset of the exact attachments"));
        LoadedExpected.Add(Package);
    }
    if (!Expected.Contains(OverlayPackage) || !LoadedExpected.Contains(OverlayPackage)
        || !LoadedExpected.Contains(Root+TEXT("CampaignRoutingCandidate"))
        || !LoadedExpected.Contains(Root+TEXT("Layers/Residents")))
        return Fail(TEXT("Campaign overlay, router and residents must remain attached and loaded"));
    TMap<FString,ULevel*> Loaded;
    for (const auto* Stream:World->GetStreamingLevels())
    {
        if (!Stream || !Expected.Remove(Stream->GetWorldAssetPackageName()))
            return Fail(TEXT("The actual attachment inventory differs from its receipt"));
        if (auto* Level=Stream->GetLoadedLevel())
        {
            const FString Package=Stream->GetWorldAssetPackageName();
            if (!LoadedExpected.Remove(Package) || !Stream->IsLevelVisible())
                return Fail(TEXT("Unexpected loaded or hidden layer; preserve current streaming state"));
            Loaded.Add(Package,Level);
        }
    }
    if (!Expected.IsEmpty() || !LoadedExpected.IsEmpty())
        return Fail(TEXT("The receipted attachment and loaded inventories are incomplete"));
    AWarSiegeBattlefield* Field=nullptr;
    for (TActorIterator<AWarSiegeBattlefield> It(World);It;++It)
    {
        if (Field || It->GetLevel()!=Loaded.FindRef(OverlayPackage))
            return Fail(TEXT("Exactly one battlefield must remain in the owned overlay"));
        Field=*It;
    }
    FString Error;
    const auto* City=Field ? Field->CityDefinition.Get() : nullptr;
    if (!Field || Field->DefinitionVersion!=2 || !Field->bLiveCapitalOverlay || Field->Capital!=TEXT("aegis_capital")
        || !City || City->GetOutermost()->GetName()!=Root+TEXT("City") || City->Revision!=CityRevision
        || !City->Validate(Error))
        return Fail(TEXT("The live eight-anchor battlefield and exact shared city must remain bound"));
    for (const FName Package:City->Packages())
        if (!UWarCityDefinition::ValidateLevel(Loaded.FindRef(Package.ToString()),Error))
            return Fail(TEXT("Every shared scenery layer must be fully available and valid"));
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav || !Nav->SupportsNavigationGeneration()) return Fail(TEXT("Editor navigation generation is unavailable"));
    TArray<ARecastNavMesh*> Data;
    bool Default=false,Convoy=false;
    for (TActorIterator<ARecastNavMesh> It(World);It;++It)
    {
        if (It->GetLevel()!=World->PersistentLevel || It->GetRuntimeGenerationMode()!=ERuntimeGenerationType::Static)
            return Fail(TEXT("Only the existing persistent static profiles may rebuild"));
        const auto& Config=It->GetConfig();
        if (Config.Name==TEXT("Default") && Config.AgentRadius==42.f && Config.AgentHeight==192.f && !Default
            && It->GetFName()==TEXT("RecastNavMesh-Default")) Default=true;
        else if (Config.Name==TEXT("SiegeConvoy") && Config.AgentRadius==320.f && Config.AgentHeight==330.f && !Convoy
            && It->GetFName()==TEXT("RecastNavMesh-SiegeConvoy")) Convoy=true;
        else return Fail(TEXT("Navigation profiles differ from the approved character and convoy"));
        Data.Add(*It);
    }
    if (Data.Num()!=2 || !Default || !Convoy) return Fail(TEXT("Both existing persistent agent profiles are required"));
    ANavMeshBoundsVolume* Bounds=nullptr;ANavMeshBoundsVolume* Duplicate=nullptr;
    for (TActorIterator<ANavMeshBoundsVolume> It(World);It;++It)
    {
        if (It->GetFName()!=TEXT("NavMeshBoundsVolume_0") || !It->Tags.Contains(TEXT("WarSiegeNavigation")))
            return Fail(TEXT("Unowned navigation bounds must be preserved"));
        if (It->GetLevel()==World->PersistentLevel && !Bounds) Bounds=*It;
        else if (It->GetLevel()==Loaded.FindRef(OverlayPackage) && !Duplicate) Duplicate=*It;
        else return Fail(TEXT("Conflicting navigation bounds ownership"));
    }
    const FBox ApprovedBounds(FVector(-26000,-18000,-6000),FVector(44000,18000,19000));
    // Navigation bounds deliberately have NoCollision; include those components exactly as the engine does.
    if (!Bounds || Bounds->GetComponentsBoundingBox(true)!=ApprovedBounds
        || (Duplicate && (!Duplicate->GetActorTransform().Equals(Bounds->GetActorTransform())
            || Duplicate->GetComponentsBoundingBox(true)!=ApprovedBounds)))
        return Fail(TEXT("Only the identical duplicate of the approved retained bounds may be removed"));
    TArray<TObjectPtr<AActor>> Props=Field->WarEffortProps;Props.Append(Field->GateMechanisms);
    TArray<ANavModifierVolume*> Modifiers;
    for (TActorIterator<ANavModifierVolume> It(World);It;++It)
    {
        if (!It->Tags.Contains(TEXT("WarSiegePropNavigation"))) continue;
        if (It->GetLevel()!=Field->GetLevel() || It->GetAreaClass()!=UNavArea_Null::StaticClass())
            return Fail(TEXT("Preserve conflicting objective navigation exclusions"));
        Modifiers.Add(*It);
    }
    if (Props.Num()!=5 || Modifiers.Num()!=5) return Fail(TEXT("All five existing prop and gate exclusions are required"));
    for (const auto& Prop:Props)
        if (!IsValid(Prop) || Prop->GetLevel()!=Field->GetLevel())
            return Fail(TEXT("Every objective prop must remain in its owned live overlay"));
    // Preflight is complete. Retain every service, router, gate and authored modifier.
    // Only the exact redundant bounds actor is removed; the caller backs up both maps.
    if (Duplicate)
    {
        Duplicate->Modify();Duplicate->GetLevel()->Modify();
        Nav->OnNavigationBoundsRemoved(Duplicate);
        if (!World->DestroyActor(Duplicate)) return Fail(TEXT("Duplicate bounds removal failed; use rollback before saving"));
        Loaded.FindRef(OverlayPackage)->MarkPackageDirty();
    }
    FlushAsyncLoading();World->FlushLevelStreaming(EFlushLevelStreamingType::Full);
    FAssetCompilingManager::Get().FinishAllCompilation();
    Nav->RemoveNavigationBuildLock(ENavigationBuildLock::AsyncLoadLock,UNavigationSystemV1::ELockRemovalRebuildAction::NoRebuild);
    Nav->OnNavigationBoundsUpdated(Bounds);Nav->Tick(0.f);
    Nav->Build();
    for (auto* Actor:Data)
        if (!Actor->IsRegistered() || Actor->GetNumActiveTiles()<=0 || Actor->NeedsRebuild() || TileSnapshot(Actor).IsEmpty())
            return Fail(TEXT("Fresh registered tile payloads are incomplete; do not save"));
    if (Nav->IsNavigationBuildInProgress() || Nav->IsNavigationDirty())
        return Fail(TEXT("Fresh navigation still needs rebuilding; do not save"));
    World->PersistentLevel->MarkPackageDirty();
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),true);
    Report->SetBoolField(TEXT("rebuilt"),true);Report->SetBoolField(TEXT("duplicateBoundsRemoved"),Duplicate!=nullptr);
    Report->SetBoolField(TEXT("runtimeVerified"),false);Report->SetBoolField(TEXT("productionAdmission"),false);
    Report->SetStringField(TEXT("navigation"),DescribeBakedNavigation(World));
    FString Result;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Result));return Result;
}

FString UWarSiegeAuthoringLibrary::OwnCampaignNavigation(UWorld* World,const FString& OverlayPackage)
{
    const auto Fail=[](const TCHAR* Reason)
    { UE_LOG(LogTemp,Warning,TEXT("WAR_CAMPAIGN_NAV_OWNERSHIP_BLOCKED %s"),Reason);return FString(Reason); };
    if (!World || World->IsGameWorld() || !World->PersistentLevel
        || !IsPrivateCampaignNavigationPair(World->GetOutermost()->GetName(),OverlayPackage))
        return Fail(TEXT("Only an exact private campaign and matching overlay may transfer navigation"));
    TArray<ARecastNavMesh*> Data;
    for (TActorIterator<ARecastNavMesh> It(World);It;++It)
    {
        if (It->GetLevel()==World->PersistentLevel)
            return Fail(TEXT("Preserve existing persistent navigation; transfer would conflict"));
        if (It->GetLevel()->GetOutermost()->GetName()==OverlayPackage) Data.Add(*It);
    }
    if (Data.Num()!=2) return Fail(TEXT("Both baked scenario profiles are required"));
    ANavMeshBoundsVolume* Bounds=nullptr;
    for (TActorIterator<ANavMeshBoundsVolume> It(World);It;++It)
    {
        if (!It->Tags.Contains(TEXT("WarSiegeNavigation"))) continue;
        if (Bounds || It->GetLevel()->GetOutermost()->GetName()!=OverlayPackage)
            return Fail(TEXT("Preserve conflicting or unowned siege navigation bounds"));
        Bounds=*It;
    }
    if (!Bounds || FindObjectFast<UObject>(World->PersistentLevel,Bounds->GetFName())
        || !Bounds->Rename(nullptr,World->PersistentLevel,REN_Test))
        return Fail(TEXT("The exact baked siege bounds must move without replacing objects"));
    bool Default=false,Convoy=false;
    TArray<FString> Before;
    for (const auto* Actor:Data)
    {
        const auto& Config=Actor->GetConfig();
        if (Config.Name==TEXT("Default") && Config.AgentRadius==42.f && Config.AgentHeight==192.f && !Default) Default=true;
        else if (Config.Name==TEXT("SiegeConvoy") && Config.AgentRadius==320.f && Config.AgentHeight==330.f && !Convoy) Convoy=true;
        else return Fail(TEXT("Navigation profiles differ from the approved character and convoy"));
        if (Actor->GetRuntimeGenerationMode()!=ERuntimeGenerationType::Static || Actor->GetNumActiveTiles()<=0)
            return Fail(TEXT("Existing static baked tiles are required; this operation never rebuilds"));
        if (FindObjectFast<UObject>(World->PersistentLevel,Actor->GetFName())
            || !const_cast<ARecastNavMesh*>(Actor)->Rename(nullptr,World->PersistentLevel,REN_Test))
            return Fail(TEXT("Navigation names cannot move without replacing existing objects"));
        Before.Add(TileSnapshot(Actor));
        if (Before.Last().IsEmpty()) return Fail(TEXT("Cannot witness the complete baked tile payload"));
    }
    TArray<TSharedPtr<FJsonValue>> Rows;
    const FString OldBoundsPath=Bounds->GetPathName();
    const FTransform BoundsTransform=Bounds->GetActorTransform();
    const FBox BoundsBox=Bounds->GetComponentsBoundingBox();
    auto* BoundsLevel=Bounds->GetLevel();
    Bounds->Modify();BoundsLevel->Modify();World->PersistentLevel->Modify();
    if (!Bounds->Rename(nullptr,World->PersistentLevel,REN_DontCreateRedirectors)
        || Bounds->GetLevel()!=World->PersistentLevel || BoundsLevel->Actors.Contains(Bounds)
        || !World->PersistentLevel->Actors.Contains(Bounds) || !Bounds->GetActorTransform().Equals(BoundsTransform)
        || Bounds->GetComponentsBoundingBox()!=BoundsBox)
        return Fail(TEXT("Bounds ownership transfer failed; preserve rollback packages before saving"));
    BoundsLevel->MarkPackageDirty();World->PersistentLevel->MarkPackageDirty();
    // AActor::Rename updates both levels' actor/GC lists. Clipboard level moves omit baked native data.
    for (int32 I=0;I<Data.Num();++I)
    {
        auto* Actor=Data[I];auto* Source=Actor->GetLevel();const FString OldPath=Actor->GetPathName();
        Actor->Modify();Source->Modify();World->PersistentLevel->Modify();
        if (!Actor->Rename(nullptr,World->PersistentLevel,REN_DontCreateRedirectors)
            || Actor->GetLevel()!=World->PersistentLevel || Source->Actors.Contains(Actor)
            || !World->PersistentLevel->Actors.Contains(Actor) || TileSnapshot(Actor)!=Before[I])
            return Fail(TEXT("Navigation transfer failed; preserve rollback packages before saving"));
        Source->MarkPackageDirty();World->PersistentLevel->MarkPackageDirty();
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("before"),OldPath);
        Row->SetStringField(TEXT("after"),Actor->GetPathName());Row->SetStringField(TEXT("profile"),Actor->GetConfig().Name.ToString());
        Row->SetNumberField(TEXT("activeTiles"),Actor->GetNumActiveTiles());Row->SetStringField(TEXT("tileSnapshot"),Before[I]);
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),true);
    auto BoundRow=MakeShared<FJsonObject>();BoundRow->SetStringField(TEXT("before"),OldBoundsPath);
    BoundRow->SetStringField(TEXT("after"),Bounds->GetPathName());Report->SetObjectField(TEXT("bounds"),BoundRow);
    Report->SetArrayField(TEXT("actors"),Rows);Report->SetBoolField(TEXT("rebuilt"),false);
    Report->SetBoolField(TEXT("runtimeVerified"),false);FString Result;
    FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Result));return Result;
}
