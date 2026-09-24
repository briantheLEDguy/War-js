#include "WarSiegeAuthoringLibrary.h"
#include "Builders/CubeBuilder.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "AssetCompilingManager.h"
#include "ActorFactories/ActorFactory.h"
#include "Engine/LevelStreaming.h"
#include "EditorLevelUtils.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"

bool UWarSiegeAuthoringLibrary::BuildNavigation(UWorld* World, FVector Center, FVector Extent)
{
    if (!World || World->IsGameWorld() || World->GetOutermost()->GetName() != TEXT("/Game/Capitals/Siege/AegisCapital_Siege")
        || World->GetCurrentLevel() != World->PersistentLevel
        || Center.ContainsNaN() || Extent.ContainsNaN() || Extent.GetMin() <= 0) return false;
    ANavMeshBoundsVolume* Bounds = nullptr;
    for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It)
        if (It->Tags.Contains(TEXT("WarSiegeNavigation"))) { Bounds = *It; break; }
    if (!Bounds) Bounds = World->SpawnActor<ANavMeshBoundsVolume>();
    if (!Bounds) return false;
    Bounds->Tags.AddUnique(TEXT("WarSiegeNavigation"));
    Bounds->SetActorLabel(TEXT("Siege navigation bounds"));
    Bounds->SetActorLocation(Center);
    auto* Builder = NewObject<UCubeBuilder>();
    Builder->X = Extent.X * 2; Builder->Y = Extent.Y * 2; Builder->Z = Extent.Z * 2;
    UActorFactory::CreateBrushForVolumeActor(Bounds, Builder);
    Bounds->SetActorLocation(Center);
    Bounds->PostEditChange();
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav) return false;
    FlushAsyncLoading();
    World->FlushLevelStreaming(EFlushLevelStreamingType::Full);
    // Empty inherited campaign layers have no actors and escaped the original
    // actor inventory. Remove their streaming records as well as loaded levels.
    const auto Streams = World->GetStreamingLevels();
    for (ULevelStreaming* Stream : Streams)
    {
        if (!Stream || Stream->GetWorldAssetPackageName() == TEXT("/Game/Capitals/Siege/AegisCityGeometry")) continue;
        if (auto* Level = Stream->GetLoadedLevel())
        {
            if (!EditorLevelUtils::RemoveLevelFromWorld(Level)) return false;
        }
        else World->RemoveStreamingLevel(Stream);
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    // The commandlet has no editor ticker to release the completed async-load lock.
    Nav->RemoveNavigationBuildLock(ENavigationBuildLock::AsyncLoadLock, UNavigationSystemV1::ELockRemovalRebuildAction::NoRebuild);
    Nav->OnNavigationBoundsUpdated(Bounds);
    Nav->Tick(0.f);
    UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_NAV_LEVELS %d"), World->GetLevels().Num());
    Nav->Build();
    return true;
}
bool UWarSiegeAuthoringLibrary::NavigationBusy(UWorld* World)
{
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    return Nav && Nav->IsNavigationBuildInProgress();
}
FString UWarSiegeAuthoringLibrary::ProbeNavigation(UWorld* World, const TArray<FVector>& Points)
{
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav) return TEXT("Navigation unavailable");
    FString Result;
    for (int32 I = 0; I < Points.Num(); ++I)
    {
        FNavLocation Projected;
        const bool Found = Nav->ProjectPointToNavigation(Points[I], Projected, FVector(100,100,250));
        auto* Path = Found && !Points.IsEmpty() ? UNavigationSystemV1::FindPathToLocationSynchronously(World, Points[0], Projected.Location) : nullptr;
        Result += FString::Printf(TEXT("%d projected=%d connected=%d position=%s\n"), I, Found,
            Found && (FVector::DistSquared(Points[0], Projected.Location) < FMath::Square(100.f)
                || (Path && Path->IsValid() && !Path->IsPartial())), *Projected.Location.ToString());
    }
    return Result;
}
AActor* UWarSiegeAuthoringLibrary::CreateAssembly(UWorld* World, const FString& Label,
    const TArray<UStaticMesh*>& Meshes, const TArray<FTransform>& Transforms, bool bStageGate)
{
    if (!World || World->IsGameWorld() || World->GetOutermost()->GetName() != TEXT("/Game/Capitals/Siege/AegisCapital_Siege")
        || Meshes.IsEmpty() || Meshes.Num() != Transforms.Num()) return nullptr;
    for (int32 I = 0; I < Meshes.Num(); ++I)
        if (!Meshes[I] || Transforms[I].ContainsNaN()) return nullptr;
    auto* Actor = World->SpawnActor<AStaticMeshActor>();
    if (!Actor) return nullptr;
    Actor->SetActorLabel(Label);
    Actor->Tags.Add(TEXT("WarSiegeObjectiveProp"));
    for (int32 I = 0; I < Meshes.Num(); ++I)
    {
        auto* Part = I == 0 ? Actor->GetStaticMeshComponent() : NewObject<UStaticMeshComponent>(Actor, NAME_None, RF_Transactional);
        if (I > 0) { Actor->AddInstanceComponent(Part); Part->SetupAttachment(Actor->GetRootComponent()); }
        Part->SetStaticMesh(Meshes[I]);
        Part->SetWorldTransform(Transforms[I]);
        Part->SetCollisionProfileName(TEXT("BlockAll"));
        // Gates disappear at milestones. Keep the through-route in the static
        // navmesh; physical collision still prevents premature passage.
        Part->SetCanEverAffectNavigation(!bStageGate);
        if (I > 0) Part->RegisterComponent();
    }
    Actor->MarkPackageDirty();
    return Actor;
}
