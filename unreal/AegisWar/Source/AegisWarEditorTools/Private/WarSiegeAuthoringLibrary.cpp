#include "WarSiegeAuthoringLibrary.h"
#include "WarSiegeBattlefield.h"
#include "WarCityDefinition.h"
#include "WarCharacter.h"
#include "WarCitadelNavigationFilter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Builders/CubeBuilder.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavModifierVolume.h"
#include "NavAreas/NavArea_Null.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "NavFilters/NavigationQueryFilter.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "AssetCompilingManager.h"
#include "ActorFactories/ActorFactory.h"
#include "Engine/LevelStreaming.h"
#include "EditorLevelUtils.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"

namespace
{
    bool IsSiegeAuthoringWorld(const UWorld* World)
    {
        if (!World || World->IsGameWorld()) return false;
        const FString Package=World->GetOutermost()->GetName();
        if (Package==TEXT("/Game/Capitals/Siege/AegisCapital_Siege")) return true;
        const FString Prefix=TEXT("/Game/WorldRebuild/AegisCitadel_");
        const FString Suffix=TEXT("/SiegeCandidate");
        if (!Package.StartsWith(Prefix) || !Package.EndsWith(Suffix)) return false;
        const FString Revision=Package.Mid(Prefix.Len(),Package.Len()-Prefix.Len()-Suffix.Len());
        if (Revision.Len()!=12) return false;
        for (const TCHAR C : Revision)
            if (!((C>=TEXT('0') && C<=TEXT('9')) || (C>=TEXT('a') && C<=TEXT('f')))) return false;
        return true;
    }
}

bool UWarSiegeAuthoringLibrary::BuildNavigation(UWorld* World, FVector Center, FVector Extent)
{
    const auto Fail=[](const FString& Reason)
    { UE_LOG(LogTemp, Error, TEXT("WAR_SIEGE_NAV_BLOCKED %s"), *Reason); return false; };
    if (!IsSiegeAuthoringWorld(World)
        || World->GetCurrentLevel() != World->PersistentLevel
        || Center.ContainsNaN() || Extent.ContainsNaN() || Extent.GetMin() <= 0)
        return Fail(TEXT("Invalid authoring world, current level or bounds"));
    ANavMeshBoundsVolume* Bounds = nullptr;
    for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It)
        if (It->Tags.Contains(TEXT("WarSiegeNavigation"))) { Bounds = *It; break; }
    if (!Bounds) Bounds = World->SpawnActor<ANavMeshBoundsVolume>();
    if (!Bounds) return Fail(TEXT("Cannot create navigation bounds"));
    Bounds->Tags.AddUnique(TEXT("WarSiegeNavigation"));
    Bounds->SetActorLabel(TEXT("Siege navigation bounds"));
    Bounds->SetActorLocation(Center);
    auto* Builder = NewObject<UCubeBuilder>();
    Builder->X = Extent.X * 2; Builder->Y = Extent.Y * 2; Builder->Z = Extent.Z * 2;
    UActorFactory::CreateBrushForVolumeActor(Bounds, Builder);
    Bounds->SetActorLocation(Center);
    Bounds->PostEditChange();
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav) return Fail(TEXT("Navigation system unavailable"));
    FlushAsyncLoading();
    World->FlushLevelStreaming(EFlushLevelStreamingType::Full);
    const UWarCityDefinition* City = nullptr;
    for (TActorIterator<AWarSiegeBattlefield> It(World); It; ++It) City = It->CityDefinition;
    FString Error;
    if (!City || !City->Validate(Error)) return Fail(TEXT("Invalid shared city definition: ")+Error);
    TSet<FName> Expected(City->Packages());
    for (const auto* Stream : World->GetStreamingLevels())
    {
        if (!Stream || !Expected.Remove(Stream->GetWorldAssetPackageFName())
            || !UWarCityDefinition::ValidateLevel(Stream->GetLoadedLevel(), Error))
            return Fail(TEXT("Unexpected or invalid scenery level: ")
                +(Stream ? Stream->GetWorldAssetPackageName() : TEXT("null"))+TEXT(" ")+Error);
    }
    if (!Expected.IsEmpty()) return Fail(TEXT("Shared city scenery is not fully attached"));
    // Multipart supply props have narrow gaps which Recast can rasterize as
    // walkable even though the character capsule cannot pass their collision.
    // Exclude each complete assembly; gates retain their milestone through-route.
    TArray<ANavModifierVolume*> OldModifiers;
    for (TActorIterator<ANavModifierVolume> It(World); It; ++It)
        if (It->GetLevel() == World->PersistentLevel && It->Tags.Contains(TEXT("WarSiegePropNavigation"))) OldModifiers.Add(*It);
    for (auto* Modifier : OldModifiers) World->DestroyActor(Modifier);
    for (TActorIterator<AWarSiegeBattlefield> It(World); It; ++It)
    {
        TArray<TObjectPtr<AActor>> Props = It->WarEffortProps;
        Props.Append(It->GateMechanisms);
        for (const auto& Prop : Props)
        {
            if (!IsValid(Prop) || Prop->GetLevel() != World->PersistentLevel)
                return Fail(TEXT("Objective prop missing or outside owned overlay"));
            FVector Origin, Size; Prop->GetActorBounds(true, Origin, Size);
            if (Size.GetMin() <= 0) return Fail(TEXT("Objective prop lacks collision bounds: ")+Prop->GetName());
            auto* Modifier = World->SpawnActor<ANavModifierVolume>();
            if (!Modifier) return Fail(TEXT("Cannot create prop navigation exclusion"));
            Modifier->Tags.Add(TEXT("WarSiegePropNavigation"));
            Modifier->SetActorLabel(Prop->GetActorLabel() + TEXT(" navigation exclusion"));
            auto* Shape = NewObject<UCubeBuilder>();
            // Area modifiers are not eroded like solid geometry. Include the
            // pedestrian radius and two raster cells so corner paths clear it.
            const float Clearance = 42.f + 2.f * 19.f;
            Shape->X = (Size.X + Clearance) * 2; Shape->Y = (Size.Y + Clearance) * 2; Shape->Z = Size.Z * 2 + 20;
            UActorFactory::CreateBrushForVolumeActor(Modifier, Shape);
            Modifier->SetActorLocation(Origin);
            Modifier->SetAreaClass(UNavArea_Null::StaticClass());
            Modifier->PostEditChange();
        }
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
FString UWarSiegeAuthoringLibrary::ProbeNavigation(UWorld* World, const TArray<FVector>& Points, int32 DiagnosticMaxSearchNodes)
{
    if (DiagnosticMaxSearchNodes < 0 || DiagnosticMaxSearchNodes > 8192)
        return TEXT("Diagnostic navigation search budget is outside its bounded range");
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav) return TEXT("Navigation unavailable");
    // The world also contains convoy navigation. Pedestrian routes must use
    // the playable character's agent, independently of nav-data registration order.
    const FNavAgentProperties Agent = GetDefault<AWarCharacter>()->GetCharacterMovement()->GetNavAgentPropertiesRef();
    const auto* Data = Nav->GetNavDataForProps(Agent, Points.IsEmpty() ? FVector::ZeroVector : Points[0]);
    if (!Data) return TEXT("Playable character navigation unavailable");
    auto Filter = Data->GetDefaultQueryFilter()->GetCopy();
    if (IsSiegeAuthoringWorld(World))
        for (TActorIterator<AWarSiegeBattlefield> It(World); It; ++It)
            if (It->DefinitionVersion == 2)
            {
                Filter = UNavigationQueryFilter::GetQueryFilter(*Data, *It,
                    UWarCitadelNavigationFilter::StaticClass())->GetCopy();
                break;
            }
    if (DiagnosticMaxSearchNodes > 0) Filter->SetMaxSearchNodes(DiagnosticMaxSearchNodes);
    UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_NAV_AGENT %s radius=%.1f height=%.1f main=%s"),
        *Data->GetConfig().Name.ToString(), Data->GetConfig().AgentRadius, Data->GetConfig().AgentHeight,
        Nav->GetDefaultNavDataInstance() ? *Nav->GetDefaultNavDataInstance()->GetConfig().Name.ToString() : TEXT("none"));
    FString Result;
    for (int32 I = 0; I < Points.Num(); ++I)
    {
        FNavLocation Projected;
        const bool Found = Nav->ProjectPointToNavigation(Points[I], Projected, FVector(100,100,250), Data);
        bool Connected = false;
        bool SearchLimit = false;
        int32 QueryResult = INDEX_NONE;
        if (Found && !Points.IsEmpty())
        {
            FPathFindingQuery Query(nullptr, *Data, Points[0], Projected.Location, Filter);
            Query.SetAllowPartialPaths(false);
            const auto Path = Nav->FindPathSync(Agent, Query);
            QueryResult = static_cast<int32>(Path.Result);
            SearchLimit = Path.Path.IsValid() && Path.Path->DidSearchReachedLimit();
            Connected = FVector::DistSquared(Points[0], Projected.Location) < FMath::Square(100.f)
                || (Path.IsSuccessful() && Path.Path.IsValid() && !Path.Path->IsPartial());
        }
        Result += FString::Printf(TEXT("%d projected=%d connected=%d position=%s searchLimit=%d result=%d budget=%d\n"), I, Found,
            Connected, *Projected.Location.ToString(), SearchLimit, QueryResult,
            Filter->GetMaxSearchNodes());
    }
    return Result;
}
AActor* UWarSiegeAuthoringLibrary::CreateAssembly(UWorld* World, const FString& Label,
    const TArray<UStaticMesh*>& Meshes, const TArray<FTransform>& Transforms, bool bStageGate)
{
    if (!IsSiegeAuthoringWorld(World)
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
