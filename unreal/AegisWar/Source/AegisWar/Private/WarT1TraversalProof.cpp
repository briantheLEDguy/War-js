#include "WarT1TraversalProof.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarZoneAnchor.h"
#include "WarZoneLightingSubsystem.h"
#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformTime.h"

namespace
{
bool Enabled()
{
    return !UE_BUILD_SHIPPING && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentNetworking"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarT1TraversalProof"));
}
TArray<TSharedPtr<FJsonValue>> Position(const FVector& P)
{
    return {MakeShared<FJsonValueNumber>(P.X), MakeShared<FJsonValueNumber>(P.Y), MakeShared<FJsonValueNumber>(P.Z)};
}
}

AWarT1TraversalGameMode::AWarT1TraversalGameMode()
{
    DefaultPawnClass = nullptr;
    HUDClass = nullptr;
    PlayerStateClass = AWarPlayerState::StaticClass();
    PlayerControllerClass = AWarPlayerController::StaticClass();
}
void AWarT1TraversalGameMode::StartPlay()
{
    if (!Enabled()) { FPlatformMisc::RequestExitWithStatus(false, 1); return; }
    Super::StartPlay();
}
void AWarT1TraversalGameMode::PreLogin(const FString& Options, const FString& Address,
    const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage)
{
    Super::PreLogin(Options, Address, UniqueId, ErrorMessage);
    // This fixture never authorizes a remote account or production session.
    if (!Enabled() || (Address != TEXT("127.0.0.1") && Address != TEXT("::1") && Address != TEXT("::ffff:127.0.0.1")))
        ErrorMessage = TEXT("T1 traversal is an isolated local development fixture.");
}
bool UWarT1TraversalProof::ShouldCreateSubsystem(UObject* Outer) const
{ return Enabled() && Super::ShouldCreateSubsystem(Outer); }
bool UWarT1TraversalProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game; }
TStatId UWarT1TraversalProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarT1TraversalProof, STATGROUP_Tickables); }
bool UWarT1TraversalProof::ValidSelector(const FString& Selector)
{
    TArray<FString> Parts; Selector.ParseIntoArray(Parts, TEXT("/"), false);
    if (Parts.Num() != 2 || Parts[0].IsEmpty() || Parts[0].Len() > 80) return false;
    for (TCHAR C : Parts[0]) if (!FChar::IsDigit(C) && C != TEXT('-')) return false;
    return Parts[1] == TEXT("sunmeadow_march.json") || Parts[1] == TEXT("cinderfen_outskirts.json");
}
bool UWarT1TraversalProof::ValidCandidate(const FString& Package, const FString& Identity)
{
    if (Identity != TEXT("sunmeadow_march") && Identity != TEXT("cinderfen_outskirts")) return false;
    if ((!Package.StartsWith(TEXT("/Game/WorldRebuild/T1Redesign_Homes_"))
        && !Package.StartsWith(TEXT("/Game/WorldRebuild/T1Redesign_Materials_"))) || Package.Contains(TEXT(".."))) return false;
    TArray<FString> Parts; Package.ParseIntoArray(Parts, TEXT("/"), true);
    return Parts.Num() == 5 && Parts[3] == Identity && Parts[4] == TEXT("Review");
}
bool UWarT1TraversalProof::InitializeProof(FString& Error)
{
    FString Selector, Json;
    if (!FParse::Value(FCommandLine::Get(), TEXT("WarT1TraversalConfig="), Selector) || !ValidSelector(Selector))
    { Error = TEXT("Traversal config must select a bounded Saved/T1Traversal run and admitted zone."); return false; }
    const FString File = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("T1Traversal"), Selector);
    Directory = FPaths::GetPath(File); Directory /= FPaths::GetBaseFilename(File);
    IFileManager::Get().MakeDirectory(*Directory, true);
    if (!FFileHelper::LoadFileToString(Json, *File) || Json.Len() > 1024*1024
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Config) || !Config.IsValid())
    { Error = TEXT("Traversal config missing or invalid."); return false; }
    FString Map, VisualPath, Signature;
    const TArray<TSharedPtr<FJsonValue>>* InputRoutes = nullptr;
    if (!Config->TryGetStringField(TEXT("zone"), Zone) || !Config->TryGetStringField(TEXT("map"), Map)
        || !Config->TryGetStringField(TEXT("visual"), VisualPath) || !Config->TryGetStringField(TEXT("signature"), Signature)
        || Signature.Len() != 64 || !ValidCandidate(Map, Zone) || GetWorld()->GetPackage()->GetName() != Map
        || GetWorld()->GetNetMode() == NM_Client || !Config->TryGetArrayField(TEXT("routes"), InputRoutes)
        || InputRoutes->IsEmpty() || InputRoutes->Num() > 80)
    { Error = TEXT("Traversal requires the matching isolated authority candidate and bounded routes."); return false; }
    const bool Aegis = Zone == TEXT("sunmeadow_march");
    const FString RequiredVisual = Aegis ? TEXT("/Game/MigrationProof/Visual_civic_sunfire_templar_m")
        : TEXT("/Game/MigrationProof/Visual_mire_warbrute_m");
    if (VisualPath != RequiredVisual) { Error = TEXT("Traversal character identity differs from its regional fixture."); return false; }
    int32 Anchors = 0;
    for (TActorIterator<AWarZoneAnchor> It(GetWorld()); It; ++It) if (It->ZoneId == FName(Zone)) ++Anchors;
    if (Anchors != 1) { Error = TEXT("Candidate requires one matching spatial anchor."); return false; }
    auto* Visual = LoadObject<UWarCharacterVisualDefinition>(nullptr, *VisualPath);
    if (!Visual || !Visual->ValidateForSpawn(Aegis ? EWarRealm::Aegis : EWarRealm::Riftbound, Error)) return false;
    Routes = *InputRoutes;
    Config->TryGetBoolField(TEXT("capture"), bCapture);
    AWarPlayerState* State = nullptr;
    if (auto* Player = GetWorld()->GetFirstPlayerController())
    { Controller = Player; State = Player->GetPlayerState<AWarPlayerState>(); }
    else
    {
        Controller = GetWorld()->SpawnActor<AAIController>();
        State = GetWorld()->SpawnActor<AWarPlayerState>();
    }
    if (!Controller.IsValid() || !State || (bCapture && GetWorld()->GetNetMode() == NM_DedicatedServer))
    { Error = TEXT("Traversal controller, state or rendering surface unavailable."); return false; }
    State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(FName(Zone));
    FVector Ground;
    const TArray<TSharedPtr<FJsonValue>>* First = nullptr;
    const auto FirstRoute = Routes[0]->AsObject();
    if (!FirstRoute || !FirstRoute->TryGetArrayField(TEXT("points"), First) || First->IsEmpty()
        || !GroundPoint((*First)[0]->AsObject(), Ground, Error)) return false;
    FTransform Spawn(FRotator::ZeroRotator, Ground + FVector(0, 0, 100));
    auto* Character = GetWorld()->SpawnActorDeferred<AWarCharacter>(AWarCharacter::StaticClass(), Spawn, nullptr, nullptr,
        ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding);
    if (!Character) { Error = TEXT("Native traversal spawn is blocked."); return false; }
    Pawn = Character;
    Character->SetPlayerState(State);
    if (!Character->SetVisualDefinition(Visual, Error)) return false;
    Character->FinishSpawning(Spawn);
    Controller->Possess(Character); Character->SetPlayerState(State); State->InitializeForPawn(Character);
    Character->GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Character->SetCameraIndoorMode(false);
    WallStarted = FPlatformTime::Seconds();
    return StartRoute(Error);
}
bool UWarT1TraversalProof::GroundPoint(const TSharedPtr<FJsonObject>& Point, FVector& Ground, FString& Error) const
{
    const TArray<TSharedPtr<FJsonValue>>* Coordinates = nullptr; bool Terrain = false;
    if (!Point || !Point->TryGetArrayField(TEXT("position"), Coordinates) || Coordinates->Num() != 3
        || !Point->TryGetBoolField(TEXT("terrain"), Terrain))
    { Error = TEXT("Traversal waypoint is malformed."); return false; }
    FVector Expected;
    for (int32 I = 0; I < 3; ++I)
    {
        double N;
        if (!(*Coordinates)[I]->TryGetNumber(N) || !FMath::IsFinite(N) || FMath::Abs(N) > 300000)
        { Error = TEXT("Traversal coordinates exceed the bounded candidate."); return false; }
        Expected[I] = N;
    }
    FCollisionQueryParams Query(SCENE_QUERY_STAT(T1TraversalFloor), true);
    if (Pawn.IsValid()) Query.AddIgnoredActor(Pawn.Get());
    if (Terrain) for (TActorIterator<AActor> It(GetWorld()); It; ++It)
        if (It->ActorHasTag(TEXT("WarT1PrototypeScenery"))) Query.AddIgnoredActor(*It);
    FHitResult Hit;
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Expected + FVector(0, 0, Terrain ? 20000 : 40),
        Expected - FVector(0, 0, Terrain ? 20000 : 150), ECC_Visibility, Query) || Hit.ImpactNormal.Z < .71)
    { Error = TEXT("Traversal waypoint has no walkable native floor."); return false; }
    Ground = Hit.ImpactPoint;
    const auto* Anchor = AWarZoneAnchor::FindAt(GetWorld(), Ground);
    if (!Anchor || Anchor->ZoneId != FName(Zone) || !Anchor->ContainsPlayablePoint(Ground, 42))
    { Error = TEXT("Traversal waypoint leaves the admitted playable outline."); return false; }
    return true;
}
bool UWarT1TraversalProof::StartRoute(FString& Error)
{
    ++Route;
    if (Route == Routes.Num()) { Finish(true, TEXT("All configured native character routes completed.")); return true; }
    const auto Input = Routes[Route]->AsObject(); const TArray<TSharedPtr<FJsonValue>>* Points = nullptr;
    FString Id, Kind;
    if (!Input || !Input->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty() || Id.Len() > 140
        || Id.Contains(TEXT("/")) || Id.Contains(TEXT("\\")) || Id.Contains(TEXT(".."))
        || !Input->TryGetStringField(TEXT("kind"), Kind) || !Input->TryGetArrayField(TEXT("points"), Points)
        || Points->Num() < 2 || Points->Num() > 2000)
    { Error = TEXT("Traversal route is malformed or unbounded."); return false; }
    Targets.Reset(); CapturePoints.Reset(); Captured.Reset();
    for (const auto& Point : *Points)
    {
        FVector Ground; const auto Object = Point->AsObject();
        if (!GroundPoint(Object, Ground, Error)) return false;
        Targets.Add(Ground); bool Capture = false; Object->TryGetBoolField(TEXT("capture"), Capture);
        if (Capture) CapturePoints.Add(Targets.Num()-1);
    }
    InputScale = Kind == TEXT("home") ? .4f : 1.f;
    // Only route starts are repositioned. Every subsequent waypoint must be reached by native walking.
    Pawn->GetCharacterMovement()->StopMovementImmediately();
    if (!Pawn->SetActorLocation(Targets[0] + FVector(0, 0, 99), false, nullptr, ETeleportType::TeleportPhysics))
    { Error = TEXT("Native traversal could not position the route start."); return false; }
    Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    Pawn->SetCameraIndoorMode(false);
    Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("id"), Id); Row->SetStringField(TEXT("kind"), Kind);
    Row->SetNumberField(TEXT("waypoints"), Targets.Num()); Row->SetNumberField(TEXT("reachedWaypoints"), 1);
    Row->SetArrayField(TEXT("startFeet"), Position(Targets[0]));
    RouteStarted = GetWorld()->GetTimeSeconds(); SettleUntil = RouteStarted + .5; Waypoint = 1;
    Previous = Pawn->GetActorLocation(); Distance = Stalled = Airborne = LongestAirborne = 0;
    bScreenshotRequested = false; CaptureUntil = 0;
    UE_LOG(LogTemp, Display, TEXT("WAR_T1_WALK_START %s points=%d"), *Id, Targets.Num());
    return true;
}
void UWarT1TraversalProof::CompleteRoute()
{
    Pawn->GetCharacterMovement()->StopMovementImmediately();
    Row->SetBoolField(TEXT("completed"), true); Row->SetNumberField(TEXT("distanceCm"), Distance);
    Row->SetNumberField(TEXT("simulatedSeconds"), GetWorld()->GetTimeSeconds() - RouteStarted);
    Row->SetNumberField(TEXT("longestAirborneSeconds"), LongestAirborne);
    Row->SetNumberField(TEXT("inRouteTeleports"), 0); Row->SetNumberField(TEXT("jumps"), 0);
    Row->SetArrayField(TEXT("finishFeet"), Position(Pawn->GetActorLocation() - FVector(0, 0, 96)));
    Results.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp, Display, TEXT("WAR_T1_WALKED %s distance=%.1fcm"), *Row->GetStringField(TEXT("id")), Distance);
    Row.Reset();
}
void UWarT1TraversalProof::Finish(bool Passed, const FString& Detail)
{
    bFinished = true;
    auto Report = MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"), Passed);
    Report->SetStringField(TEXT("detail"), Detail); Report->SetStringField(TEXT("zone"), Zone);
    Report->SetStringField(TEXT("map"), GetWorld()->GetPackage()->GetName());
    if (Config) Report->SetStringField(TEXT("signature"), Config->GetStringField(TEXT("signature")));
    Report->SetNumberField(TEXT("routesCompleted"), Results.Num()); Report->SetArrayField(TEXT("routes"), Results);
    if (Row) Report->SetObjectField(TEXT("unfinishedRoute"), Row);
    Report->SetNumberField(TEXT("frames"), Frames); Report->SetNumberField(TEXT("wallSeconds"), FPlatformTime::Seconds()-WallStarted);
    Report->SetBoolField(TEXT("fixedTimeStep"), FParse::Param(FCommandLine::Get(), TEXT("benchmark")));
    Report->SetBoolField(TEXT("drivingAccepted"), false); Report->SetBoolField(TEXT("visualApproved"), false);
    Report->SetBoolField(TEXT("cameraAccepted"), false); Report->SetBoolField(TEXT("gameplayAccepted"), false);
    if (Pawn.IsValid())
    {
        Report->SetBoolField(TEXT("visibleCharacterReady"), Pawn->IsVisualReady());
        Report->SetBoolField(TEXT("developmentFlight"), Pawn->IsDevelopmentFlying());
        Report->SetNumberField(TEXT("capsuleRadiusCm"), Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius());
        Report->SetNumberField(TEXT("capsuleHalfHeightCm"), Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        Report->SetNumberField(TEXT("maxStepHeightCm"), Pawn->GetCharacterMovement()->MaxStepHeight);
        Report->SetNumberField(TEXT("maxWalkSpeedCm"), Pawn->GetCharacterMovement()->MaxWalkSpeed);
        Report->SetStringField(TEXT("visual"), Pawn->GetVisualDefinition()->GetPathName());
    }
    FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    if (!Directory.IsEmpty()) FFileHelper::SaveStringToFile(Json, *FPaths::Combine(Directory, TEXT("report.json")));
    UE_LOG(LogTemp, Display, TEXT("WAR_T1_TRAVERSAL passed=%d routes=%d %s"), Passed, Results.Num(), *Detail);
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}
void UWarT1TraversalProof::Tick(float Delta)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    ++Frames; const double Now = GetWorld()->GetTimeSeconds(); if (Started < 0) Started = Now;
    FString Error;
    if (!bInitialized)
    {
        if (Now-Started < 1) return;
        if (!InitializeProof(Error)) { Finish(false, Error); return; }
        bInitialized = true; return;
    }
    if (!Pawn.IsValid() || !Controller.IsValid() || !Pawn->IsVisualReady() || Pawn->IsDead() || Pawn->IsDevelopmentFlying()
        || Pawn->GetCapsuleComponent()->GetCollisionEnabled() == ECollisionEnabled::NoCollision
        || !FMath::IsNearlyEqual(Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius(), 42.f)
        || !FMath::IsNearlyEqual(Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(), 96.f)
        || !FMath::IsNearlyEqual(Pawn->GetCharacterMovement()->MaxStepHeight, 45.f)
        || !FMath::IsNearlyEqual(Pawn->GetCharacterMovement()->MaxWalkSpeed, 600.f))
    { Finish(false, TEXT("Traversal lost its normal visible colliding character.")); return; }
    if (Now < SettleUntil) { Previous = Pawn->GetActorLocation(); return; }
    const FVector Location = Pawn->GetActorLocation(), Feet = Location - FVector(0, 0, 96);
    const double Moved = FVector::Dist2D(Location, Previous); Distance += Moved; Previous = Location;
    Airborne = Pawn->GetCharacterMovement()->IsMovingOnGround() ? 0 : Airborne + Delta;
    LongestAirborne = FMath::Max(LongestAirborne, Airborne);
    const auto* Anchor = AWarZoneAnchor::FindAt(GetWorld(), Feet);
    if (Airborne > .75 || !Anchor || !Anchor->ContainsPlayablePoint(Feet, 42))
    { Finish(false, TEXT("Traversal lost ground support or left its playable outline.")); return; }
    if (bCapture) UWarZoneLightingSubsystem::PreviewEnvironment(GetWorld(), FName(Zone), FVector::ZeroVector, 1200, 0);
    if (FVector::Dist2D(Feet, Targets[Waypoint]) < 28 && FMath::Abs(Feet.Z-Targets[Waypoint].Z) < 50
        && Pawn->GetCharacterMovement()->IsMovingOnGround())
    {
        Pawn->GetCharacterMovement()->StopMovementImmediately(); Stalled = 0;
        if (bCapture && CapturePoints.Contains(Waypoint) && !Captured.Contains(Waypoint))
        {
            if (CaptureUntil == 0) CaptureUntil = Now + 1;
            if (Now < CaptureUntil) return;
            if (!bScreenshotRequested)
            {
                FScreenshotRequest::RequestScreenshot(FPaths::Combine(Directory,
                    Row->GetStringField(TEXT("id")) + FString::Printf(TEXT("_%d.png"), Waypoint)), false, false);
                bScreenshotRequested = true; CaptureUntil = Now + .5; return;
            }
            Captured.Add(Waypoint); CaptureUntil = 0; bScreenshotRequested = false;
        }
        Row->SetNumberField(TEXT("reachedWaypoints"), ++Waypoint);
        if (Waypoint == Targets.Num()) { CompleteRoute(); if (!StartRoute(Error)) Finish(false, Error); }
        return;
    }
    Stalled = Moved > Delta*5 ? 0 : Stalled + Delta;
    if (Stalled > 4 || Now-RouteStarted > 1800)
    {
        Row->SetArrayField(TEXT("blockedFeet"), Position(Feet)); Row->SetArrayField(TEXT("target"), Position(Targets[Waypoint]));
        Row->SetNumberField(TEXT("blockedWaypoint"), Waypoint);
        FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(T1TraversalBlocked), true, Pawn.Get());
        GetWorld()->SweepSingleByChannel(Hit, Location, Targets[Waypoint] + FVector(0, 0, 96), FQuat::Identity,
            ECC_Pawn, FCollisionShape::MakeCapsule(42, 96), Query);
        Row->SetStringField(TEXT("blocker"), GetNameSafe(Hit.GetActor()));
        Finish(false, TEXT("Normal native walking stalled; geometry or waypoint repair required.")); return;
    }
    const FVector Direction = (Targets[Waypoint]-Feet).GetSafeNormal2D();
    Controller->SetControlRotation(Direction.Rotation());
    if (auto* Player = Cast<AWarPlayerController>(Controller.Get())) Player->GetLocalCameraState().Yaw = Direction.Rotation().Yaw;
    if (bCapture) Pawn->SetCameraIndoorMode(Row->GetStringField(TEXT("kind")) == TEXT("home")
        && Routes[Route]->AsObject()->GetArrayField(TEXT("points"))[Waypoint]->AsObject()->GetBoolField(TEXT("indoor")));
    Pawn->AddMovementInput(Direction, InputScale, true);
}
