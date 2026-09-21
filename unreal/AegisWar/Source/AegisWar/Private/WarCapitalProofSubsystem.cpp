#include "WarCapitalProofSubsystem.h"
#include "WarWorldEditSubsystem.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarQuestNpc.h"
#include "WarCraftingStation.h"
#include "WarResourceNode.h"
#include "EngineUtils.h"
#include "WarWorldEditPlacement.h"
#include "WarWorldEditCatalog.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "UnrealClient.h"
#include "TimerManager.h"

bool UWarCapitalProofSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarCapitalProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM"));
#endif
}
bool UWarCapitalProofSubsystem::DoesSupportWorldType(const EWorldType::Type Type) const { return Type == EWorldType::Game; }
TStatId UWarCapitalProofSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCapitalProofSubsystem, STATGROUP_Tickables); }

void UWarCapitalProofSubsystem::Finish(const bool bPassed, const FString& Detail)
{
    bFinished = true;
    FString Run; FParse::Value(FCommandLine::Get(), TEXT("WarProofRun="), Run);
    if (Run.IsEmpty() || Run.Len() > 64 || Run.Contains(TEXT("..")) || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\")))
    { FPlatformMisc::RequestExitWithStatus(false, 1); return; }
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("CapitalProof"), Run);
    IFileManager::Get().MakeDirectory(*Directory, true);
    const auto Report = MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"), 1); Report->SetBoolField(TEXT("passed"), bPassed);
    Report->SetStringField(TEXT("detail"), Detail); Report->SetBoolField(TEXT("fullCapitalAcceptance"), false);
    Report->SetBoolField(TEXT("sharedGmAuthorization"), false);
    Report->SetBoolField(TEXT("surfacePlacementVerified"), bSurfacePlacementVerified);
    Report->SetBoolField(TEXT("constructionRowVerified"), bConstructionRowVerified);
    Report->SetBoolField(TEXT("castleTraversalVerified"), bCastleTraversalVerified);
    Report->SetNumberField(TEXT("castleRoutesWalked"), CastleRouteIndex);
    Report->SetNumberField(TEXT("surfaceModelsVerified"), SurfaceModelsVerified);
    Report->SetBoolField(TEXT("developmentTraversalVerified"), bTraversalVerified);
    Report->SetBoolField(TEXT("capitalGameplayIntegrationVerified"), bGameplayIntegrationVerified);
    Report->SetNumberField(TEXT("capitalResourcesVerified"), CapitalResourcesVerified);
    Report->SetBoolField(TEXT("placementSnappingVerified"), bPlacementSnappingVerified);
    Report->SetBoolField(TEXT("catalogSearchVerified"), bCatalogSearchVerified);
    Report->SetBoolField(TEXT("exactTransformVerified"), bExactTransformVerified);
    Report->SetBoolField(TEXT("worldPickingVerified"), bWorldPickingVerified);
    Report->SetNumberField(TEXT("walkableWallCount"), WalkableWallCount);
    Report->SetBoolField(TEXT("constructionReload"), FParse::Param(FCommandLine::Get(), TEXT("WarCapitalReloadProof")));
    if (const auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
    {
        Report->SetNumberField(TEXT("editableObjects"), Editor->GetHistory().GetObjects().Num());
        Report->SetNumberField(TEXT("retainedBaselineAdditions"), Editor->GetHistory().GetLoadedBaselineAdditions());
        Report->SetStringField(TEXT("isolatedDraft"), Editor->GetDraftLocation());
    }
    FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json, *FPaths::Combine(Directory, TEXT("report.json")));
    const bool bCapture=bPassed && FParse::Param(FCommandLine::Get(), TEXT("WarProofScreenshot"));
    if (bCapture)
    {
        const FString Image = FPaths::Combine(Directory, TEXT("builder.png"));
        FTimerHandle Capture;
        // Let recreated mesh render state and shader precaching settle after undo/redo.
        GetWorld()->GetTimerManager().SetTimer(Capture, [Image] { FScreenshotRequest::RequestScreenshot(Image, true, false); }, 3.f, false);
    }
    FTimerHandle Exit;
    GetWorld()->GetTimerManager().SetTimer(Exit, [bPassed] { FPlatformMisc::RequestExitWithStatus(false, bPassed ? 0 : 1); }, bCapture ? 5.f : 2.f, false);
}

void UWarCapitalProofSubsystem::Tick(const float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (StartedAt < 0) StartedAt = Now;
    auto* Player = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Character = Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!Character || !Editor || (Stage < 3 && !Character->GetCharacterMovement()->IsMovingOnGround()))
    {
        if (Now - StartedAt > 30) Finish(false, TEXT("Capital character failed to reach authored ground."));
        return;
    }
    if (Stage == 11) { TickCastleTraversal(); return; }
    if (Stage == 10)
    {
        if (Now - CityWalkStartedAt > 240)
        { Finish(false, FString::Printf(TEXT("Grounded capital walk stalled at waypoint %d: %s"), CityRouteIndex, *Character->GetActorLocation().ToString())); return; }
        while (CityRoute.IsValidIndex(CityRouteIndex)
            && FVector::Dist2D(Character->GetActorLocation(), CityRoute[CityRouteIndex]) < 75)
            ++CityRouteIndex;
        if (!CityRoute.IsValidIndex(CityRouteIndex))
        {
            Character->GetCharacterMovement()->StopMovementImmediately();
            bTraversalVerified = Character->GetCharacterMovement()->IsMovingOnGround();
            Finish(bTraversalVerified, TEXT("Default game city: grounded ascent, quest/station interactions, GM construction and draft save verified.")); return;
        }
        FVector Direction = CityRoute[CityRouteIndex] - Character->GetActorLocation(); Direction.Z = 0;
        Character->AddMovementInput(Direction.GetSafeNormal(), 1.f);
        return;
    }
    if (Stage == 3)
    {
        if (Character->GetActorLocation().Z - FlightPosition.Z < 100)
        {
            if (Now - FlightStartedAt > 5) { Finish(false, TEXT("GM vertical flight did not move the character.")); return; }
            Character->AddMovementInput(FVector::UpVector, 1.f); return;
        }
        Player->ServerReturnToDevelopmentSpawn();
        if (FVector::Dist2D(Character->GetActorLocation(), StartPosition) > 200)
        { Finish(false, TEXT("GM return did not reach capital arrival.")); return; }
        Player->ServerSetDevelopmentTraversal(false, 1.f);
        if (Character->IsDevelopmentFlying() || Character->GetCapsuleComponent()->GetCollisionEnabled() == ECollisionEnabled::NoCollision
            || Character->GetCharacterMovement()->MaxWalkSpeed != 600.f)
        { Finish(false, TEXT("GM walking did not restore collision and speed.")); return; }
        Stage = 4; FlightStartedAt = Now; return;
    }
    if (Stage == 4)
    {
        if (!Character->GetCharacterMovement()->IsMovingOnGround())
        { if (Now - FlightStartedAt > 5) Finish(false, TEXT("GM return did not recover grounded walking.")); return; }
        bTraversalVerified = true; Player->ToggleWorldEditor();
        Finish(true, TEXT("Capital construction/drafts, collision, modal controls and GM flight/speed/return passed.")); return;
    }
    if (Stage == 0)
    {
        if (FParse::Param(FCommandLine::Get(), TEXT("WarCrownwardProof")))
        {
            FString Error;
            const auto CheckCity = [this](bool Passed, const FString& Detail) { if (!Passed) Finish(false, Detail); return Passed; };
            int32 Expected = 0;
            if (!CheckCity(FParse::Value(FCommandLine::Get(), TEXT("WarCapitalExpectedObjects="), Expected)
                && Expected > 0 && Editor->Open(Player, Error), TEXT("City GM open failed: ") + Error)) return;
            if (!CheckCity(Editor->GetHistory().GetObjects().Num() == Expected, TEXT("City object count differs."))) return;
            const auto Catalog = WarWorldEditCatalog::Build(Editor->GetHistory().GetBaselineObjects());
            int32 ExpectedModels = 0;
            if (!CheckCity(FParse::Value(FCommandLine::Get(), TEXT("WarCapitalExpectedModels="), ExpectedModels)
                && ExpectedModels > 0 && Catalog.Num() == ExpectedModels, TEXT("City authored model catalog count differs."))) return;
            bCatalogSearchVerified = true;
            if (FParse::Param(FCommandLine::Get(), TEXT("WarCastleTraversalProof")))
            { StartCastleTraversal(); return; }
            if (FParse::Param(FCommandLine::Get(), TEXT("WarConstructionRowProof")))
            { RunConstructionRowProof(); return; }
            if (FParse::Param(FCommandLine::Get(), TEXT("WarSurfacePlacementProof")))
            { RunSurfacePlacementProof(); return; }
            if (FParse::Param(FCommandLine::Get(), TEXT("WarCapitalReloadProof")))
            {
                if (!CheckCity(Editor->LoadDraft(Player, 0, Error)
                    && Editor->GetHistory().GetObjects().Num() == Expected + 1, TEXT("City fresh-process draft reload failed: ") + Error)) return;
                Finish(true, TEXT("Crownward construction survived a fresh process.")); return;
            }
            FCollisionQueryParams Query(SCENE_QUERY_STAT(WarCrownwardRoute), false);
            Query.AddIgnoredActor(Character);
            FString FixtureJson;
            TSharedPtr<FJsonObject> Fixture;
            const TArray<TSharedPtr<FJsonValue>>* RouteValues = nullptr;
            if (!CheckCity(FFileHelper::LoadFileToString(FixtureJson, *FPaths::Combine(FPaths::ProjectContentDir(),
                TEXT("Migration/capital-development.json")))
                && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(FixtureJson), Fixture)
                && Fixture.IsValid() && Fixture->TryGetArrayField(TEXT("routes"), RouteValues)
                && RouteValues->Num() > 2 && RouteValues->Num() < 2000, TEXT("Missing capital route fixture."))) return;
            TArray<FVector> Route;
            for (const auto& Value : *RouteValues)
            {
                const TArray<TSharedPtr<FJsonValue>>* XYZ = nullptr;
                if (!CheckCity(Value->TryGetArray(XYZ) && XYZ->Num() == 3, TEXT("Invalid capital route point."))) return;
                FVector Point((*XYZ)[0]->AsNumber(), (*XYZ)[1]->AsNumber(), (*XYZ)[2]->AsNumber());
                if (!CheckCity(!Point.ContainsNaN() && Point.GetAbsMax() < 100000, TEXT("Invalid capital route bounds."))) return;
                Route.Add(Point);
            }
            for (int32 Index = 1; Index < Route.Num(); ++Index)
            {
                FHitResult Hit;
                // Sweep within the character's step envelope. The subsequent actual
                // grounded walk proves these small terrain variations are traversable.
                const FVector StepAllowance(0,0,Character->GetCharacterMovement()->MaxStepHeight);
                const bool bBlocked = GetWorld()->SweepSingleByChannel(Hit, Route[Index - 1] + StepAllowance, Route[Index] + StepAllowance, FQuat::Identity, ECC_Pawn,
                    FCollisionShape::MakeCapsule(Character->GetCapsuleComponent()->GetScaledCapsuleRadius(),
                        Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Query);
                if (!CheckCity(!bBlocked,
                    FString::Printf(TEXT("City route blocked at segment %d by %s: %s"), Index,
                        Hit.GetActor() ? *Hit.GetActor()->GetActorNameOrLabel() : TEXT("none"), *Hit.ImpactPoint.ToString()))) return;
                FFindFloorResult Floor;
                Character->GetCharacterMovement()->FindFloor(Route[Index], Floor, false);
                if (!CheckCity(Floor.IsWalkableFloor(), FString::Printf(TEXT("City route has no walkable floor at %d."), Index))) return;
            }
            const FVector Arrival = Character->GetActorLocation();
            AWarQuestNpc* Dispatch = nullptr;
            for (TActorIterator<AWarQuestNpc> It(GetWorld()); It; ++It)
                if (It->NpcId == TEXT("quest-1") && It->ZoneId == TEXT("aegis_capital")) Dispatch = *It;
            auto* State = Character->GetPlayerState<AWarPlayerState>();
            if (!CheckCity(Dispatch && State, TEXT("Main-game dispatch NPC or player state missing."))) return;
            const int32 Revision = State->GetInventory().Revision;
            if (!CheckCity(!State->InteractQuest(Dispatch, TEXT("dawnline-01-scouting"), false, Revision, Error),
                TEXT("Capital quest accepted from outside interaction range."))) return;
            Character->SetActorLocation(Dispatch->GetActorLocation() + FVector(100,0,100), false, nullptr, ETeleportType::TeleportPhysics);
            if (!CheckCity(State->InteractQuest(Dispatch, TEXT("dawnline-01-scouting"), false, Revision, Error)
                && State->GetInventory().Quests.Num() == 1
                && !State->InteractQuest(Dispatch, TEXT("dawnline-01-scouting"), false, Revision, Error),
                TEXT("Capital quest acceptance/retry check failed: ") + Error)) return;
            TSet<FName> StationKinds;
            for (TActorIterator<AWarCraftingStation> It(GetWorld()); It; ++It)
            {
                Character->SetActorLocation(It->GetActorLocation() + FVector(100,0,100), false, nullptr, ETeleportType::TeleportPhysics);
                if (!CheckCity(It->CanInteract(Character), TEXT("Capital station does not accept nearby interaction."))) return;
                Character->SetActorLocation(It->GetActorLocation() + FVector(5000,0,100), false, nullptr, ETeleportType::TeleportPhysics);
                if (!CheckCity(!It->CanInteract(Character), TEXT("Capital station accepts out-of-range interaction."))) return;
                StationKinds.Add(It->StationKind);
            }
            if (!CheckCity(StationKinds.Num() == 5 && StationKinds.Contains(TEXT("general"))
                && StationKinds.Contains(TEXT("apothecary")) && StationKinds.Contains(TEXT("cultivation"))
                && StationKinds.Contains(TEXT("talisman_making")) && StationKinds.Contains(TEXT("salvage")),
                TEXT("Capital lost source crafting station kinds."))) return;
            TSet<FName> ExpectedNodes{TEXT("aegis_capital_herb_node_03"),TEXT("aegis_capital_soil_node_04"),
                TEXT("aegis_capital_scrap_node_01"),TEXT("aegis_capital_ore_node_02"),
                TEXT("aegis_capital_scrap_node_07"),TEXT("aegis_capital_ore_node_08")};
            for (TActorIterator<AWarResourceNode> It(GetWorld()); It; ++It)
            {
                if (!CheckCity(It->ZoneId==TEXT("aegis_capital") && ExpectedNodes.Remove(It->NodeId)==1,
                    TEXT("Unexpected or duplicate capital gathering node."))) return;
                FWarResourceDefinition Definition;
                const int32 Before=State->GetInventory().Revision;
                Character->SetActorLocation(It->GetActorLocation()+FVector(1000,0,100),false,nullptr,ETeleportType::TeleportPhysics);
                if (!CheckCity(!State->GatherResource(*It,Before,Error) && State->GetInventory().Revision==Before,
                    TEXT("Distant gathering changed inventory."))) return;
                Character->SetActorLocation(It->GetActorLocation()+FVector(100,0,100),false,nullptr,ETeleportType::TeleportPhysics);
                It->SetActorHiddenInGame(true);
                const bool HiddenRejected=!State->GatherResource(*It,Before,Error);
                It->SetActorHiddenInGame(false);
                if (!CheckCity(HiddenRejected && It->ResolveInteraction(Character,Definition,Error),
                    TEXT("Gathering visual/range validation failed."))) return;
                const auto* Previous=State->GetInventory().Professions.FindByPredicate([&](const auto& Row){return Row.Profession==Definition.Profession;});
                const int32 PreviousXp=Previous ? Previous->Xp : 0;
                if (!CheckCity(State->GatherResource(*It,Before,Error) && State->GetInventory().Revision==Before+1
                    && !State->GatherResource(*It,Before,Error) && !State->GatherResource(*It,Before+1,Error)
                    && State->GetInventory().Revision==Before+1,TEXT("Gather/retry/cooldown checks failed."))) return;
                const auto* Progress=State->GetInventory().Professions.FindByPredicate([&](const auto& Row){return Row.Profession==Definition.Profession;});
                if (!CheckCity(Progress && Progress->Xp==PreviousXp+Definition.Xp
                    && State->GetInventory().ResourceCooldowns.ContainsByPredicate([&](const auto& Row){return Row.NodeId==It->NodeId && Row.ZoneId==It->ZoneId;}),
                    TEXT("Gathering did not apply source profession XP/cooldown."))) return;
                ++CapitalResourcesVerified;
            }
            if (!CheckCity(ExpectedNodes.IsEmpty() && CapitalResourcesVerified==6,TEXT("Capital gathering bindings missing."))) return;
            Character->SetActorLocation(Arrival, false, nullptr, ETeleportType::TeleportPhysics);
            bGameplayIntegrationVerified = true;
            const auto& Template = Editor->GetHistory().GetBaselineObjects()[0];
            FTransform Transform = Template.Transform; Transform.AddToTranslation(FVector(0,0,5000));
            FName Created;
            if (!CheckCity(Editor->Create(Player, Template.Id, Transform, 0, Created, Error), TEXT("City construction failed: ") + Error)) return;
            if (!CheckCity(Editor->Undo(Player, false, 1, Error) && Editor->Undo(Player, true, 2, Error), TEXT("City undo/redo failed: ") + Error)) return;
            const bool bSaved = Editor->SaveDraft(Player, 3, Error);
            if (!CheckCity(bSaved, TEXT("City save failed: ") + Error)) return;
            CityRoute = MoveTemp(Route); CityRouteIndex = 0; CityWalkStartedAt = Now;
            Character->GetCharacterMovement()->StopMovementImmediately(); Stage = 10; return;
        }
        StartPosition = Character->GetActorLocation(); Character->ToggleAutoRun(); Stage = 1; return;
    }
    if (Stage == 1)
    {
        if (FVector::Dist2D(StartPosition, Character->GetActorLocation()) < 100)
        { if (Now - StartedAt > 30) Finish(false, TEXT("Capital movement failed.")); return; }
        Character->ToggleAutoRun(); Character->GetCharacterMovement()->StopMovementImmediately(); Stage = 2;
    }
    FString Error;
    const auto Check = [this](const bool Passed, const FString& Detail) { if (!Passed) Finish(false, Detail); return Passed; };
    int32 ExpectedObjects = 0;
    if (!Check(FParse::Value(FCommandLine::Get(), TEXT("WarCapitalExpectedObjects="), ExpectedObjects)
        && ExpectedObjects > 0 && ExpectedObjects <= 10000, TEXT("Missing expected authored object count."))) return;
    if (!Check(!Editor->CanUse(nullptr), TEXT("Unauthenticated workbench access allowed."))) return;
    Player->ToggleWorldEditor();
    if (!Check(Editor->GetHistory().GetObjects().Num() == ExpectedObjects && Player->IsMoveInputIgnored() && Player->IsLookInputIgnored(),
        FString::Printf(TEXT("GM panel did not open: %s; map=%s net=%d"), *Player->GetWorldEditMessage(),
            *GetWorld()->GetMapName(), static_cast<int32>(GetWorld()->GetNetMode())))) return;
    int32 ExpectedModels = 0;
    const auto Catalog = WarWorldEditCatalog::Build(Editor->GetHistory().GetBaselineObjects());
    const auto Rowhouses = WarWorldEditCatalog::Filter(Catalog, TEXT("ROWHOUSE 2"));
    if (!Check(FParse::Value(FCommandLine::Get(), TEXT("WarCapitalExpectedModels="), ExpectedModels)
        && ExpectedModels > 0 && Catalog.Num() == ExpectedModels && Rowhouses.Num() == 1
        && Editor->GetObjectActor(Rowhouses[0].TemplateId)
        && WarWorldEditCatalog::Filter(Catalog, TEXT("nonexistent kit")).IsEmpty(),
        TEXT("The native model catalog/search did not resolve trusted templates."))) return;
    bCatalogSearchVerified = true;
    int32 ExpectedWalls = 0;
    if (!Check(FParse::Value(FCommandLine::Get(), TEXT("WarCapitalExpectedWalls="), ExpectedWalls) && ExpectedWalls > 0,
        TEXT("Missing expected wall identities."))) return;
    for (const auto& Row : Editor->GetHistory().GetBaselineObjects())
    {
        auto* Wall = Editor->GetObjectActor(Row.Id);
        if (!Wall || !Wall->ActorHasTag(TEXT("aegis_wall"))) continue;
        TArray<UBoxComponent*> WallBoxes; Wall->GetComponents(WallBoxes);
        const auto* Floor = WallBoxes.FindByPredicate([](const auto* Box) { return Box->GetName() == TEXT("AuthoredCollision_3"); });
        if (!Check(WallBoxes.Num() == 4 && Floor != nullptr, TEXT("Authored wall lost its walkway."))) return;
        for (const double Offset : { -0.5, 0.0, 0.5 })
        {
            const FVector Extent = (*Floor)->GetUnscaledBoxExtent();
            FVector Standing = (*Floor)->GetComponentTransform().TransformPosition(FVector(0, Extent.Y * Offset, Extent.Z));
            Standing.Z += Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2;
            FFindFloorResult Result;
            Character->GetCharacterMovement()->FindFloor(Standing, Result, false);
            if (!Check(Result.IsWalkableFloor() && Result.HitResult.GetActor() == Wall,
                FString::Printf(TEXT("Character floor sweep failed on wall walkway %s."), *Row.Id.ToString()))) return;
        }
        ++WalkableWallCount;
    }
    if (!Check(WalkableWallCount == ExpectedWalls, TEXT("Wall walkway identities are incomplete."))) return;
    if (FParse::Param(FCommandLine::Get(), TEXT("WarCapitalKitProof")))
    {
        int32 KitMeshes = 0;
        for (const auto& Row : Editor->GetHistory().GetBaselineObjects())
        {
            auto* KitActor = Cast<AStaticMeshActor>(Editor->GetObjectActor(Row.Id));
            if (!KitActor || !KitActor->ActorHasTag(TEXT("WarKitPilot"))) continue;
            const auto Bounds = KitActor->GetStaticMeshComponent()->Bounds;
            FHitResult Hit;
            if (!Check(GetWorld()->LineTraceSingleByChannel(Hit, Bounds.Origin + FVector(0, 0, Bounds.BoxExtent.Z + 100),
                Bounds.Origin - FVector(0, 0, Bounds.BoxExtent.Z + 100), ECC_Visibility) && Hit.GetActor() == KitActor,
                FString::Printf(TEXT("Kit pilot collision missing or obstructed: %s"), *Row.Id.ToString()))) return;
            if (Row.Id == TEXT("kit_pilot_doorway"))
            {
                const auto* Capsule = Character->GetCapsuleComponent();
                const double Bottom = Bounds.Origin.Z - Bounds.BoxExtent.Z;
                FVector Center(Bounds.Origin.X, Bounds.Origin.Y, Bottom + Capsule->GetScaledCapsuleHalfHeight() + 2);
                FCollisionQueryParams Query(SCENE_QUERY_STAT(WarKitDoorway)); Query.AddIgnoredActor(Character);
                // The authored timber threshold is a real step. Measure it and
                // require the character's configured step height before sweeping.
                FHitResult Threshold;
                const float StepHeight = Character->GetCharacterMovement()->MaxStepHeight;
                if (GetWorld()->LineTraceSingleByChannel(Threshold, FVector(Center.X, Center.Y, Bottom + StepHeight),
                    FVector(Center.X, Center.Y, Bottom - 5), ECC_Visibility, Query) && Threshold.GetActor() == KitActor)
                {
                    if (!Check(Threshold.ImpactPoint.Z - Bottom <= StepHeight, TEXT("Door threshold exceeds character step height."))) return;
                    Center.Z = Threshold.ImpactPoint.Z + Capsule->GetScaledCapsuleHalfHeight() + 2;
                }
                const bool bBlocked = GetWorld()->SweepSingleByChannel(Hit, Center - FVector(0, 150, 0), Center + FVector(0, 150, 0),
                    FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),
                        Capsule->GetScaledCapsuleHalfHeight()), Query);
                if (!Check(!bBlocked, FString::Printf(TEXT("Kit doorway blocks capsule: actor=%s point=%s normal=%s penetrating=%d"),
                    Hit.GetActor() ? *Hit.GetActor()->GetActorNameOrLabel() : TEXT("none"), *Hit.ImpactPoint.ToString(),
                    *Hit.ImpactNormal.ToString(), Hit.bStartPenetrating))) return;
            }
            ++KitMeshes;
        }
        if (!Check(KitMeshes == 5, TEXT("Kit pilot mesh identities are incomplete."))) return;
    }
    const auto CheckCreated = [&](const FName CreatedId) {
        const auto* Row = Editor->GetHistory().Find(CreatedId);
        auto* CreatedActor = Cast<AStaticMeshActor>(Editor->GetObjectActor(CreatedId));
        auto* TemplateActor = Row ? Cast<AStaticMeshActor>(Editor->GetObjectActor(Row->TemplateId)) : nullptr;
        if (!Check(Row && CreatedActor && TemplateActor && !CreatedActor->IsHidden()
            && CreatedActor->GetStaticMeshComponent()->GetStaticMesh() == TemplateActor->GetStaticMeshComponent()->GetStaticMesh()
            && CreatedActor->GetActorTransform().Equals(Row->Transform, 0.01), TEXT("Created building lost its authored model or transform."))) return false;
        TArray<UBoxComponent*> CreatedBoxes; CreatedActor->GetComponents(CreatedBoxes);
        TArray<UBoxComponent*> TemplateBoxes; TemplateActor->GetComponents(TemplateBoxes);
        if (CreatedBoxes.IsEmpty() && TemplateBoxes.IsEmpty())
        {
            auto* Mesh = CreatedActor->GetStaticMeshComponent();
            auto* SourceMesh = TemplateActor->GetStaticMeshComponent();
            if (!Check(Mesh->GetCollisionProfileName() == TEXT("BlockAll")
                && Mesh->GetNumMaterials() == SourceMesh->GetNumMaterials(), TEXT("Kit collision/material configuration was lost."))) return false;
            for (int32 Index = 0; Index < Mesh->GetNumMaterials(); ++Index)
                if (!Check(Mesh->GetMaterial(Index) == SourceMesh->GetMaterial(Index), TEXT("Kit material changed on construction."))) return false;
            const auto Bounds = Mesh->Bounds;
            FHitResult Hit;
            if (!Check(GetWorld()->LineTraceSingleByChannel(Hit, Bounds.Origin + FVector(0, 0, Bounds.BoxExtent.Z + 100),
                Bounds.Origin - FVector(0, 0, Bounds.BoxExtent.Z + 100), ECC_Visibility) && Hit.GetActor() == CreatedActor,
                TEXT("Kit construction lost authored mesh collision."))) return false;
            FFindFloorResult Floor;
            Character->GetCharacterMovement()->FindFloor(Hit.ImpactPoint + FVector(0, 0,
                Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2), Floor, false);
            return Check(Floor.IsWalkableFloor() && Floor.HitResult.GetActor() == CreatedActor,
                TEXT("Constructed kit floor cannot support the character capsule."));
        }
        if (!Check(!CreatedBoxes.IsEmpty() && CreatedBoxes.Num() == TemplateBoxes.Num(), TEXT("Created building lost authored collision."))) return false;
        // The wall floor sits above the body volume; test that authored top rather than an occluded interior face.
        const auto* Walkway = CreatedBoxes.FindByPredicate([](const auto* Box) { return Box->GetName() == TEXT("AuthoredCollision_3"); });
        const auto* Box = Walkway ? *Walkway : CreatedBoxes[0]; const FVector Center = Box->GetComponentLocation(), Extent = Box->GetScaledBoxExtent();
        FHitResult Hit;
        return Check(GetWorld()->LineTraceSingleByChannel(Hit, Center + FVector(0, 0, Extent.Z + 25), Center, ECC_Visibility)
            && Hit.GetActor() == CreatedActor && FMath::Abs(Hit.ImpactPoint.Z - Center.Z - Extent.Z) < 0.2,
            TEXT("Created building has no blocking collision."));
    };
    if (FParse::Param(FCommandLine::Get(), TEXT("WarCapitalReloadProof")))
    {
        int32 ExpectedAdditions = 1;
        FParse::Value(FCommandLine::Get(), TEXT("WarCapitalExpectedAdditions="), ExpectedAdditions);
        Player->ServerWorldEditDraft(true, 0);
        if (!Check(Editor->GetHistory().GetObjects().Num() == ExpectedObjects + 1, TEXT("Fresh process did not restore construction draft."))) return;
        if (!Check(Editor->GetHistory().GetLoadedBaselineAdditions() == ExpectedAdditions, TEXT("Fresh process did not retain newly authored objects."))) return;
        const auto* Created = Editor->GetHistory().GetObjects().FindByPredicate([](const auto& Row) { return !Row.TemplateId.IsNone(); });
        if (!Check(Created != nullptr, TEXT("Fresh draft lost created identity.")) || !CheckCreated(Created->Id)) return;
        Finish(true, TEXT("Fresh process restored the constructed complex building, transform and blocking collision.")); return;
    }
    const FName Id(TEXT("aegis_city_house_0"));
    const auto* Initial = Editor->GetHistory().Find(Id);
    if (!Check(Initial != nullptr, TEXT("Missing edited house."))) return;
    const FTransform Original = Initial->Transform;
    FTransform Moved = Original; Moved.AddToTranslation(FVector(1200, 0, 0));
    Moved.SetRotation(FQuat(FVector::UpVector, FMath::DegreesToRadians(30.0)) * Moved.GetRotation());
    Moved.SetScale3D(Moved.GetScale3D() * 1.2);
    AActor* Actor = Editor->GetObjectActor(Id);
    TArray<UBoxComponent*> Boxes;
    if (Actor) Actor->GetComponents(Boxes);
    if (!Check(Boxes.Num() == 1, TEXT("Unexpected authored house collision."))) return;
    const FTransform ExpectedBox = Boxes[0]->GetRelativeTransform() * Moved;
    Player->ServerEditWorldObject(Id, Moved, false, 0);
    if (!Check(Actor && Actor->GetActorTransform().Equals(Moved, 0.01) && Editor->GetHistory().GetRevision() == 1,
        TEXT("Server GM transform was not applied."))) return;
    Player->ServerEditWorldObject(Id, Original, false, 0);
    if (!Check(Editor->GetHistory().GetRevision() == 1, TEXT("Stale GM edit accepted."))) return;
    const auto* Box = Boxes[0];
    if (!Check(Box->GetComponentTransform().Equals(ExpectedBox, 0.01), TEXT("Collision detached from edited model transform."))) return;
    const FVector Center = Box->GetComponentLocation(), Extent = Box->GetScaledBoxExtent();
    FHitResult Hit;
    const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, Center + FVector(0, 0, Extent.Z + 25), Center, ECC_Visibility);
    if (!Check(bHit && Hit.GetActor() == Actor && FMath::Abs(Hit.ImpactPoint.Z - Center.Z - Extent.Z) < 0.2,
        TEXT("GM transform did not preserve native collision."))) return;
    Player->ServerEditWorldObject(Id, Moved, true, 1);
    if (!Check(Actor->IsHidden() && !Actor->GetActorEnableCollision(), TEXT("Hidden GM object retained collision."))) return;
    Player->ServerWorldEditHistory(false, 2);
    if (!Check(!Actor->IsHidden() && Actor->GetActorEnableCollision(), TEXT("GM undo did not restore collision."))) return;
    Player->ServerWorldEditHistory(true, 3);
    Player->ServerWorldEditHistory(false, 4);
    Player->ServerWorldEditDraft(false, 5);
    FString Saved;
    if (!Check(FFileHelper::LoadFileToString(Saved, *Editor->GetDraftLocation()), TEXT("GM draft was not saved."))) return;
    Player->ServerEditWorldObject(Id, Original, false, 5);
    Player->ServerWorldEditDraft(true, 6);
    if (!Check(Editor->GetHistory().GetRevision() == 7 && Actor->GetActorTransform().Equals(Moved, 0.01), TEXT("GM draft reload failed."))) return;
    FFileHelper::SaveStringToFile(TEXT("{}"), *Editor->GetDraftLocation());
    Player->ServerWorldEditDraft(false, 7);
    FString External;
    FFileHelper::LoadFileToString(External, *Editor->GetDraftLocation());
    if (!Check(External == TEXT("{}"), TEXT("GM save overwrote an external draft change."))) return;
    Player->ServerWorldEditDraft(true, 7);
    if (!Check(Editor->GetHistory().GetRevision() == 7, TEXT("Malformed draft modified live world."))) return;
    FFileHelper::SaveStringToFile(Saved, *Editor->GetDraftLocation());
    Player->ServerWorldEditHistory(false, 7);
    if (!Check(Actor->GetActorTransform().Equals(Original, 0.01), TEXT("Loaded draft cannot be undone."))) return;
    FTransform GridInput = Original; GridInput.AddToTranslation(FVector(17, 23, 0));
    const auto GridAligned = WarWorldEditPlacement::SnapTransform(GridInput, 100, 90);
    Player->ServerEditWorldObject(Id, GridAligned, false, Editor->GetHistory().GetRevision());
    if (!Check(Actor->GetActorTransform().Equals(GridAligned, 0.01)
        && Boxes[0]->GetComponentTransform().Equals(Boxes[0]->GetRelativeTransform() * GridAligned, 0.01)
        && GridAligned.GetLocation().Z == Original.GetLocation().Z
        && GridAligned.GetScale3D().Equals(Original.GetScale3D()), TEXT("Grid alignment lost geometry, collision or height."))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    if (!Check(Actor->GetActorTransform().Equals(Original, 0.01), TEXT("Grid alignment could not be undone."))) return;
    bPlacementSnappingVerified = true;
    FTransform Exact = Original;
    if (!Check(WarWorldEditPlacement::SetComponent(Exact, 0, Original.GetLocation().X / 100 + 1.234)
        && WarWorldEditPlacement::SetComponent(Exact, 3, 12)
        && WarWorldEditPlacement::SetComponent(Exact, 5, -7)
        && WarWorldEditPlacement::SetComponent(Exact, 7, FMath::Abs(Original.GetScale3D().Y) * 1.25),
        TEXT("Exact transform values were rejected."))) return;
    Player->ServerEditWorldObject(Id, Exact, false, Editor->GetHistory().GetRevision());
    if (!Check(Actor->GetActorTransform().Equals(Exact, 0.01)
        && Boxes[0]->GetComponentTransform().Equals(Boxes[0]->GetRelativeTransform() * Exact, 0.01),
        TEXT("Exact transform detached model and collision."))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    if (!Check(Actor->GetActorTransform().Equals(Original, 0.01), TEXT("Exact transform could not be undone."))) return;
    bExactTransformVerified = true;
    FTransform Placed = Original; Placed.AddToTranslation(FVector(0, 0, 5000));
    const int32 BeforeCreate = Editor->GetHistory().GetRevision();
    const FName ConstructionTemplate(FParse::Param(FCommandLine::Get(), TEXT("WarCapitalKitProof"))
        ? TEXT("kit_pilot_floor") : TEXT("aegis_battle_enclosure_front_0_0"));
    if (FParse::Param(FCommandLine::Get(), TEXT("WarCapitalKitProof"))) Placed.SetScale3D(FVector::OneVector);
    Player->ServerCreateWorldObject(TEXT("unregistered"), Placed, BeforeCreate);
    if (!Check(Editor->GetHistory().GetRevision() == BeforeCreate, TEXT("Unknown building template accepted."))) return;
    Player->ServerCreateWorldObject(ConstructionTemplate, Placed, BeforeCreate - 1);
    if (!Check(Editor->GetHistory().GetRevision() == BeforeCreate, TEXT("Stale building creation accepted."))) return;
    Player->ServerCreateWorldObject(ConstructionTemplate, Placed, BeforeCreate);
    const auto* Created = Editor->GetHistory().GetObjects().FindByPredicate([](const auto& Row) { return !Row.TemplateId.IsNone(); });
    if (!Check(Created != nullptr && Editor->GetHistory().GetObjects().Num() == ExpectedObjects + 1, TEXT("GM construction failed."))) return;
    const FName CreatedId = Created->Id;
    if (!CheckCreated(CreatedId)) return;
    TArray<UBoxComponent*> PickBoxes; Editor->GetObjectActor(CreatedId)->GetComponents(PickBoxes);
    const auto* PickMesh = Cast<AStaticMeshActor>(Editor->GetObjectActor(CreatedId))->GetStaticMeshComponent();
    const FVector PickCenter = PickBoxes.IsEmpty() ? PickMesh->Bounds.Origin : PickBoxes[0]->GetComponentLocation();
    const FVector PickOrigin = PickCenter + FVector(0, 0, (PickBoxes.IsEmpty() ? PickMesh->Bounds.BoxExtent.Z : PickBoxes[0]->GetScaledBoxExtent().Z) + 100);
    if (!Check(Editor->PickObject(Player, PickOrigin, -FVector::UpVector) == CreatedId
        && Editor->PickObject(nullptr, PickOrigin, -FVector::UpVector).IsNone()
        && Editor->PickObject(Player, PickOrigin, FVector::ZeroVector).IsNone(),
        TEXT("World picking failed to resolve registered geometry or rejected access."))) return;
    // Use the clear arrival location: authored house foundations extend below terrain.
    FTransform Buried = Placed;
    Buried.SetLocation(Character->GetActorLocation() - FVector(0, 0, 6000));
    Player->ServerEditWorldObject(CreatedId, Buried, false, Editor->GetHistory().GetRevision());
    const FName OccludedPick = Editor->PickObject(Player, Character->GetActorLocation() + FVector(0, 0, 1000), -FVector::UpVector);
    if (!Check(OccludedPick.IsNone(),
        FString::Printf(TEXT("World picking selected %s through blocking terrain."), *OccludedPick.ToString()))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    const int32 PickRevision = Editor->GetHistory().GetRevision();
    Player->ServerEditWorldObject(CreatedId, Placed, true, PickRevision);
    if (!Check(Editor->PickObject(Player, PickOrigin, -FVector::UpVector) != CreatedId,
        TEXT("World picking selected a hidden building."))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    if (!Check(Editor->PickObject(Player, PickOrigin, -FVector::UpVector) == CreatedId,
        TEXT("Restored building could not be selected."))) return;
    bWorldPickingVerified = true;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    if (!Check(!Editor->GetObjectActor(CreatedId) && !Editor->GetHistory().Find(CreatedId), TEXT("Undo retained a created actor."))) return;
    Player->ServerWorldEditHistory(true, Editor->GetHistory().GetRevision());
    if (!CheckCreated(CreatedId)) return;
    Player->ServerWorldEditDraft(false, Editor->GetHistory().GetRevision());
    if (!Check(FFileHelper::LoadFileToString(Saved, *Editor->GetDraftLocation()) && Saved.Contains(CreatedId.ToString()), TEXT("Construction was not saved."))) return;
    // Model a draft written before one baseline building was imported. The
    // separate reload process must retain that new building and the GM creation.
    TSharedPtr<FJsonObject> OlderDraft, OlderBaseline;
    if (!Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Saved), OlderDraft)
        && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(OlderDraft->GetStringField(TEXT("baseline"))), OlderBaseline),
        TEXT("Could not prepare additive import fixture."))) return;
    auto BaseRows = OlderBaseline->GetArrayField(TEXT("objects"));
    const FString AddedId = BaseRows.Last()->AsObject()->GetStringField(TEXT("id"));
    BaseRows.Pop(); OlderBaseline->SetArrayField(TEXT("objects"), BaseRows);
    FString OlderBaseText; FJsonSerializer::Serialize(OlderBaseline.ToSharedRef(), TJsonWriterFactory<>::Create(&OlderBaseText));
    OlderDraft->SetStringField(TEXT("baseline"), OlderBaseText);
    auto DraftRows = OlderDraft->GetArrayField(TEXT("objects"));
    DraftRows.RemoveAll([&](const auto& Value) { return Value->AsObject()->GetStringField(TEXT("id")) == AddedId; });
    OlderDraft->SetArrayField(TEXT("objects"), DraftRows);
    FString OlderText; FJsonSerializer::Serialize(OlderDraft.ToSharedRef(), TJsonWriterFactory<>::Create(&OlderText));
    if (!Check(FFileHelper::SaveStringToFile(OlderText, *Editor->GetDraftLocation()), TEXT("Could not write earlier-baseline draft."))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    Player->ServerWorldEditDraft(true, Editor->GetHistory().GetRevision());
    if (!CheckCreated(CreatedId)) return;
    if (!Check(Editor->GetHistory().GetLoadedBaselineAdditions() == 1 && Editor->GetObjectActor(FName(*AddedId)) != nullptr,
        TEXT("Older draft removed newly imported capital content."))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    Player->ToggleInventory(); Player->ToggleWorldEditor(); Player->ToggleQuestLog(); Player->ToggleWorldEditor(); Player->ToggleWorldEditor();
    if (!Check(!Player->IsMoveInputIgnored() && !Player->IsLookInputIgnored() && !Player->bShowMouseCursor,
        TEXT("GM panel transitions left movement/camera blocked."))) return;
    FlightPosition = Character->GetActorLocation();
    Player->ServerSetDevelopmentTraversal(true, 2.f);
    if (!Check(Character->IsDevelopmentFlying() && Character->GetCharacterMovement()->MovementMode == MOVE_Flying
        && Character->GetCharacterMovement()->MaxFlySpeed == 1200.f
        && Character->GetCapsuleComponent()->GetCollisionEnabled() == ECollisionEnabled::NoCollision,
        TEXT("GM flight was not enabled with authorized speed/collision."))) return;
    Player->ServerSetDevelopmentTraversal(true, 7.f);
    if (!Check(Character->GetDevelopmentSpeed() == 2.f, TEXT("Invalid GM speed changed movement."))) return;
    Character->SetActorLocation(Boxes[0]->GetComponentLocation());
    Player->ServerSetDevelopmentTraversal(false, 1.f);
    if (!Check(Character->IsDevelopmentFlying() && Character->GetDevelopmentSpeed() == 2.f,
        TEXT("GM flight exited inside blocking geometry."))) return;
    Character->SetActorLocation(FlightPosition);
    FlightStartedAt = Now; Stage = 3;
}
