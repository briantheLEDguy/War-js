#include "WarT1NavigationAuthoringLibrary.h"
#include "WarT1NavigationPrismBuilder.h"
#include "WarSiegeAuthoringLibrary.h"
#include "WarZoneAnchor.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/LevelStreaming.h"
#include "EngineUtils.h"
#include "Builders/CubeBuilder.h"
#include "ActorFactories/ActorFactory.h"
#include "AssetCompilingManager.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "NavMesh/RecastNavMesh.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavModifierVolume.h"
#include "NavAreas/NavArea_Null.h"
#include "NavFilters/NavigationQueryFilter.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Components/BrushComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "Model.h"
#include "Engine/Polys.h"

bool UWarT1NavigationPrismBuilder::Build(UWorld* World,ABrush* Brush)
{
    if (Hull.Num()<3 || Hull.Num()>4 || !FMath::IsFinite(HalfHeight) || HalfHeight<=0 || HalfHeight>100000) return false;
    for (int32 I=0;I<Hull.Num();++I)
    {
        const auto A=Hull[I],B=Hull[(I+1)%Hull.Num()],C=Hull[(I+2)%Hull.Num()];
        const auto U=B-A,V=C-B;
        if (A.ContainsNaN() || FMath::Abs(A.X)>400000 || FMath::Abs(A.Y)>400000
            || U.SizeSquared()<1e-8 || U.X*V.Y-U.Y*V.X<=1e-8) return false;
    }
    // UnrealEd's concrete builders expose these operations through UBrushBuilder's
    // virtual interface; their nonexported implementations cannot be subclassed.
    UBrushBuilder* Builder=NewObject<UCubeBuilder>();
    Builder->BeginBrush(false,NAME_None);
    for (double Z:{-HalfHeight,HalfHeight}) for (const auto P:Hull) Builder->Vertexv(FVector(P.X,P.Y,Z));
    Builder->PolyBegin(-1);for (int32 I=0;I<Hull.Num();++I) Builder->Polyi(I);Builder->PolyEnd();
    Builder->PolyBegin(1);for (int32 I=0;I<Hull.Num();++I) Builder->Polyi(I+Hull.Num());Builder->PolyEnd();
    for (int32 I=0;I<Hull.Num();++I)
    {
        const int32 J=(I+1)%Hull.Num();Builder->Poly4i(1,I,J,J+Hull.Num(),I+Hull.Num());
    }
    return Builder->EndBrush(World,Brush);
}

namespace
{
    FString Json(const TSharedRef<FJsonObject>& Object)
    {
        FString Result;FJsonSerializer::Serialize(Object,TJsonWriterFactory<>::Create(&Result));return Result;
    }
    FString Fail(const TCHAR* Reason)
    {
        UE_LOG(LogTemp,Warning,TEXT("WAR_T1_NAV_BLOCKED %s"),Reason);
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),false);
        Report->SetStringField(TEXT("error"),Reason);return Json(Report);
    }
    AWarZoneAnchor* Anchor(UWorld* World,FName Zone)
    {
        AWarZoneAnchor* Result=nullptr;
        for (TActorIterator<AWarZoneAnchor> It(World);It;++It)
        {
            if (Result || It->ZoneId!=Zone || It->GetLevel()!=World->PersistentLevel) return nullptr;
            Result=*It;
        }
        return Result;
    }
}

FString UWarT1NavigationAuthoringLibrary::BuildNavigation(UWorld* World,FName Zone,
    const TArray<FString>& ExpectedAttachments,double MinimumHeight,double MaximumHeight)
{
    if (!IsInGameThread() || !World || World->IsGameWorld() || !World->PersistentLevel
        || World->GetCurrentLevel()!=World->PersistentLevel || !IsPrivateCandidate(World->GetOutermost()->GetName(),Zone))
        return Fail(TEXT("Only an isolated T1 navigation editor candidate may be authored"));
    auto* Region=Anchor(World,Zone);
    if (!Region || !Region->bUseSpatialBounds || !Region->ZoneOrigin.IsNearlyZero() || Region->CityDefinition)
        return Fail(TEXT("Exactly one persistent rebased T1 spatial anchor is required"));
    TArray<TArray<FVector2D>> Cells;FString Error;
    const FBox2D Horizontal(Region->ContentMin,Region->ContentMax);
    if (!ExteriorCells(Horizontal,Region->PlayableOutline,Cells,Error)) return Fail(*Error);
    if (!FMath::IsFinite(MinimumHeight) || !FMath::IsFinite(MaximumHeight) || MinimumHeight>=MaximumHeight
        || FMath::Abs(MinimumHeight)>2000000 || FMath::Abs(MaximumHeight)>2000000 || MaximumHeight-MinimumHeight>200000)
        return Fail(TEXT("Navigation requires finite bounded vertical sampling"));
    const FVector2D Size=Horizontal.GetSize();
    const int64 TileBudget=int64(FMath::CeilToInt(Size.X/4096)+2)*(FMath::CeilToInt(Size.Y/4096)+2)*2;
    if (TileBudget>16384) return Fail(TEXT("T1 footprint exceeds the bounded navigation tile inventory"));
    if (ExpectedAttachments.Num()!=2 || Region->ContentLevels.Num()!=2)
        return Fail(TEXT("The exact generated and authored T1 layers are required"));
    TSet<FString> Expected;FString LayerRoot;
    for (const FString& Package:ExpectedAttachments)
    {
        const FString Generated=TEXT("/")+Zone.ToString()+TEXT("/Generated");
        const FString Authored=TEXT("/")+Zone.ToString()+TEXT("/Authored");
        const FString Suffix=Package.EndsWith(Generated) ? Generated : Authored;
        if (!Package.StartsWith(TEXT("/Game/WorldRebuild/T1Redesign_Atmosphere_"))
            || (!Package.EndsWith(Generated) && !Package.EndsWith(Authored)) || Expected.Contains(Package)
            || !Region->ContentLevels.Contains(FName(Package)))
            return Fail(TEXT("T1 navigation must retain its exact original scenery layers"));
        const FString Root=Package.LeftChop(Suffix.Len());
        if (!LayerRoot.IsEmpty() && LayerRoot!=Root) return Fail(TEXT("Scenery layers belong to different revisions"));
        LayerRoot=Root;Expected.Add(Package);
    }
    for (const auto* Stream:World->GetStreamingLevels())
        if (!Stream || !Expected.Remove(Stream->GetWorldAssetPackageName()) || !Stream->GetLoadedLevel() || !Stream->IsLevelVisible())
            return Fail(TEXT("The attached, loaded and visible scenery inventory differs from its receipt"));
    if (!Expected.IsEmpty()) return Fail(TEXT("Required T1 scenery is missing"));
    // This operation never replaces or rebuilds existing navigation or owner content.
    for (TActorIterator<ARecastNavMesh> It(World);It;++It) return Fail(TEXT("Preserve existing navigation data"));
    for (TActorIterator<ANavMeshBoundsVolume> It(World);It;++It) return Fail(TEXT("Preserve existing navigation bounds"));
    for (TActorIterator<ANavModifierVolume> It(World);It;++It) return Fail(TEXT("Preserve existing navigation modifiers"));
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav) return Fail(TEXT("Editor navigation system is unavailable"));
    const auto& Agents=Nav->GetSupportedAgents();
    bool Default=false,Convoy=false;
    for (const auto& Agent:Agents)
    {
        if (Agent.Name==TEXT("Default") && Agent.AgentRadius==42 && Agent.AgentHeight==192 && !Default) Default=true;
        else if (Agent.Name==TEXT("SiegeConvoy") && Agent.AgentRadius==320 && Agent.AgentHeight==330 && !Convoy) Convoy=true;
        else return Fail(TEXT("Navigation profiles differ from the retained pedestrian and convoy agents"));
    }
    if (Agents.Num()!=2 || !Default || !Convoy || GetDefault<ARecastNavMesh>()->GetRuntimeGenerationMode()!=ERuntimeGenerationType::Static)
        return Fail(TEXT("Both retained static navigation agents are required"));

    FActorSpawnParameters Spawn;Spawn.OverrideLevel=World->PersistentLevel;
    const FVector Center((Horizontal.Min.X+Horizontal.Max.X)*.5,(Horizontal.Min.Y+Horizontal.Max.Y)*.5,(MinimumHeight+MaximumHeight)*.5);
    auto* Bounds=World->SpawnActor<ANavMeshBoundsVolume>(ANavMeshBoundsVolume::StaticClass(),FTransform(Center),Spawn);
    if (!Bounds) return Fail(TEXT("Cannot create private navigation bounds; discard unsaved candidate"));
    Bounds->Tags.Add(TEXT("WarT1Navigation"));Bounds->SetActorLabel(TEXT("T1 private navigation bounds"));
    auto* Cube=NewObject<UCubeBuilder>();Cube->X=Size.X;Cube->Y=Size.Y;Cube->Z=MaximumHeight-MinimumHeight;
    UActorFactory::CreateBrushForVolumeActor(Bounds,Cube);Bounds->SetActorLocation(Center);Bounds->SetActorHiddenInGame(true);Bounds->PostEditChange();
    int32 Number=0;
    for (const auto& Cell:Cells)
    {
        FBox2D CellBounds(ForceInit);for (const auto P:Cell) CellBounds+=P;
        const FVector2D Origin=CellBounds.GetCenter();
        auto* Modifier=World->SpawnActor<ANavModifierVolume>(ANavModifierVolume::StaticClass(),FTransform(FVector(Origin,Center.Z)),Spawn);
        if (!Modifier) return Fail(TEXT("Cannot create footprint exclusion; discard unsaved candidate"));
        Modifier->Tags.Add(TEXT("WarT1NavigationExterior"));
        Modifier->SetActorLabel(FString::Printf(TEXT("T1 exterior exclusion %03d"),Number++));
        auto* Prism=NewObject<UWarT1NavigationPrismBuilder>();Prism->HalfHeight=(MaximumHeight-MinimumHeight)*.5;
        for (const auto P:Cell) Prism->Hull.Add(P-Origin);
        UActorFactory::CreateBrushForVolumeActor(Modifier,Prism);
        Modifier->SetActorLocation(FVector(Origin,Center.Z));Modifier->SetAreaClass(UNavArea_Null::StaticClass());Modifier->SetActorHiddenInGame(true);Modifier->PostEditChange();
        const auto* Body=Modifier->GetBrushComponent()->GetBodySetup();
        if (!Modifier->Brush || !Modifier->Brush->Polys || Modifier->Brush->Polys->Element.Num()!=Cell.Num()+2
            || !Body || Body->AggGeom.ConvexElems.IsEmpty()
            || Modifier->GetBrushComponent()->GetCollisionEnabled()!=ECollisionEnabled::NoCollision)
            return Fail(TEXT("Convex exclusion brush is incomplete or has physical collision; do not save"));
    }
    TArray<ARecastNavMesh*> Data;
    for (const auto& Agent:Agents)
    {
        Spawn.Name=FName(TEXT("RecastNavMesh-")+Agent.Name.ToString());Spawn.bDeferConstruction=true;
        auto* Mesh=World->SpawnActor<ARecastNavMesh>(ARecastNavMesh::StaticClass(),FTransform::Identity,Spawn);
        if (!Mesh) return Fail(TEXT("Cannot create both private profiles; discard unsaved candidate"));
        Mesh->SetConfig(Agent);Mesh->SetSupportsDefaultAgent(Agent.Name==TEXT("Default"));
        Mesh->TileSizeUU=4096;Mesh->bFixedTilePoolSize=true;Mesh->TilePoolSize=16384;Mesh->TileNumberHardLimit=16384;
        if (Agent.Name==TEXT("SiegeConvoy")) Mesh->AgentMaxSlope=FMath::RadiansToDegrees(FMath::Atan(.22));
        Mesh->Tags.Add(TEXT("WarT1Navigation"));Mesh->FinishSpawning(FTransform::Identity);
        Nav->RequestRegistrationDeferred(*Mesh);Data.Add(Mesh);
    }
    FlushAsyncLoading();World->FlushLevelStreaming(EFlushLevelStreamingType::Full);
    FAssetCompilingManager::Get().FinishAllCompilation();
    Nav->RemoveNavigationBuildLock(ENavigationBuildLock::AsyncLoadLock,UNavigationSystemV1::ELockRemovalRebuildAction::NoRebuild);
    Nav->OnNavigationBoundsUpdated(Bounds);Nav->Tick(0.f);
    // A terrain-only world has no navigation octree until its first exact agent
    // is registered. Generation capability must be checked after that step.
    if (!Nav->SupportsNavigationGeneration()) return Fail(TEXT("Registered editor navigation generation is unavailable; do not save"));
    Nav->Build();
    if (Nav->IsNavigationBuildInProgress() || Nav->IsNavigationDirty())
        return Fail(TEXT("Navigation build is incomplete; do not save"));
    for (const auto* Mesh:Data)
        if (!Mesh->IsRegistered() || Mesh->GetNumActiveTiles()<=0 || Mesh->NeedsRebuild()
            || Mesh->GetRuntimeGenerationMode()!=ERuntimeGenerationType::Static)
            return Fail(TEXT("Both registered static tile payloads are required; do not save"));
    World->PersistentLevel->MarkPackageDirty();
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),true);
    Report->SetNumberField(TEXT("exteriorCells"),Cells.Num());Report->SetNumberField(TEXT("tileBudget"),TileBudget);
    Report->SetStringField(TEXT("navigation"),UWarSiegeAuthoringLibrary::DescribeBakedNavigation(World));
    Report->SetBoolField(TEXT("physicalDrivingVerified"),false);Report->SetBoolField(TEXT("productionAdmission"),false);
    return Json(Report);
}

FString UWarT1NavigationAuthoringLibrary::ProbeRoute(UWorld* World,FName Zone,bool bConvoy,const TArray<FVector>& Points)
{
    if (!IsInGameThread() || !World || World->IsGameWorld() || !IsPrivateCandidate(World->GetOutermost()->GetName(),Zone)
        || Points.Num()<2 || Points.Num()>2048) return Fail(TEXT("Bounded probes require a private T1 editor candidate"));
    const auto* Region=Anchor(World,Zone);
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Region || !Nav || Nav->IsNavigationBuildInProgress() || Nav->IsNavigationDirty()) return Fail(TEXT("Stable regional navigation is required"));
    FNavAgentProperties Agent;Agent.AgentRadius=bConvoy ? 320 : 42;Agent.AgentHeight=bConvoy ? 330 : 192;
    const auto* Data=Nav->GetNavDataForProps(Agent,Points[0]);
    const FName Profile=bConvoy ? TEXT("SiegeConvoy") : TEXT("Default");
    if (!Data || Data->GetConfig().Name!=Profile || Data->GetConfig().AgentRadius!=Agent.AgentRadius
        || Data->GetConfig().AgentHeight!=Agent.AgentHeight) return Fail(TEXT("The requested agent has no exact navigation profile"));
    TArray<TSharedPtr<FJsonValue>> Rows;bool Passed=true;FNavLocation Previous;
    bool PreviousFound=false;
    for (int32 I=0;I<Points.Num();++I)
    {
        if (Points[I].ContainsNaN()) return Fail(TEXT("Nonfinite route points are rejected"));
        FNavLocation Projected;
        const bool Found=Region->ContainsPlayablePoint(Points[I],Agent.AgentRadius)
            && Nav->ProjectPointToNavigation(Points[I],Projected,FVector(100,100,250),Data)
            && Region->ContainsPlayablePoint(Projected.Location,Agent.AgentRadius);
        bool Connected=I==0 && Found,Limit=false,WithinOutline=Found;double Length=0;
        if (I && Found && PreviousFound)
        {
            FPathFindingQuery Query(nullptr,*Data,Previous.Location,Projected.Location,Data->GetDefaultQueryFilter());
            Query.SetAllowPartialPaths(false);const auto Path=Nav->FindPathSync(Agent,Query);
            Connected=Path.IsSuccessful() && Path.Path.IsValid() && !Path.Path->IsPartial();
            Limit=Path.Path.IsValid() && Path.Path->DidSearchReachedLimit();
            if (Connected)
            {
                const auto& PathPoints=Path.Path->GetPathPoints();
                for (int32 J=1;J<PathPoints.Num();++J)
                {
                    WithinOutline &= Region->ContainsPlayableSegment(PathPoints[J-1].Location,PathPoints[J].Location,Agent.AgentRadius);
                    Length+=FVector::Dist(PathPoints[J-1].Location,PathPoints[J].Location);
                }
            }
        }
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("index"),I);
        Row->SetBoolField(TEXT("projected"),Found);Row->SetBoolField(TEXT("connected"),Connected);
        Row->SetBoolField(TEXT("withinOutline"),WithinOutline);Row->SetBoolField(TEXT("searchLimit"),Limit);
        Row->SetNumberField(TEXT("lengthCm"),Length);Row->SetStringField(TEXT("position"),Projected.Location.ToString());
        Rows.Add(MakeShared<FJsonValueObject>(Row));Passed &= Found && Connected && WithinOutline && !Limit;
        Previous=Projected;PreviousFound=Found;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetStringField(TEXT("profile"),Profile.ToString());Report->SetArrayField(TEXT("points"),Rows);
    Report->SetNumberField(TEXT("queryBudget"),Data->GetDefaultQueryFilter()->GetMaxSearchNodes());
    Report->SetBoolField(TEXT("physicalDrivingVerified"),false);return Json(Report);
}
