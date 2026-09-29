#include "WarSiegeEquipmentProof.h"
#include "WarSiegeEquipment.h"
#include "WarSiegeBattlefield.h"
#include "WarSiegeGameMode.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "UnrealClient.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"

bool UWarSiegeEquipmentProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarSiegeEquipmentProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking"));
#endif
}
bool UWarSiegeEquipmentProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarSiegeEquipmentProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarSiegeEquipmentProof,STATGROUP_Tickables); }
void UWarSiegeEquipmentProof::Finish(bool Passed,const FString& Detail)
{
    Finished=true;auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetStringField(TEXT("detail"),Detail);Report->SetNumberField(TEXT("checkpoints"),FMath::Max(0,Step-1));
    Report->SetBoolField(TEXT("stoppedWithoutEscort"),StopVerified);Report->SetBoolField(TEXT("stoppedWithoutCrew"),DeathVerified);
    Report->SetBoolField(TEXT("ramStrikeAdvanced"),StrikeVerified);
    Report->SetBoolField(TEXT("overlapRecoveredWithoutDamage"),RecoveryVerified);
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (const auto& Vehicle:Vehicles)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("position"),Vehicle->GetActorLocation().ToString());
        Row->SetNumberField(TEXT("travelCm"),Vehicle->Travel);Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    Report->SetArrayField(TEXT("vehicles"),Rows);FString Json;
    const bool Client=GetWorld()->GetNetMode()==NM_Client;
    Report->SetBoolField(TEXT("client"),Client);
    if (Client)
    {
        int32 Claims=0,Engineers=0;
        if (Battlefield) for (const auto& Flag:Battlefield->AttackerStandards) if (IsValid(Flag) && !Flag->IsHidden()) ++Claims;
        for (const auto& Vehicle:Vehicles) for (const auto& Crew:Vehicle->Engineers) if (IsValid(Crew) && Crew->IsVisualReady()) ++Engineers;
        Report->SetNumberField(TEXT("ownershipStandards"),Claims);Report->SetNumberField(TEXT("engineersReady"),Engineers);
        Report->SetNumberField(TEXT("captures"),Captured.Num());
    }
    FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*FPaths::Combine(FPaths::ProjectSavedDir(),Client ? TEXT("SiegeEquipmentClient.json") : TEXT("SiegeEquipment.json")));
    UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_EQUIPMENT passed=%d %s"),Passed,*Detail);
    FPlatformMisc::RequestExitWithStatus(false,Passed?0:1);
}
bool UWarSiegeEquipmentProof::Engineer(AWarSiegeEquipment* Vehicle,int32 Seat,FString& Error)
{
    auto* Visual=Battlefield->CrewVisual.LoadSynchronous();
    auto* Pawn=GetWorld()->SpawnActor<AWarSiegeCharacter>(Vehicle->CrewPosition(Seat)+FVector(0,0,96),FRotator::ZeroRotator);
    if (!Pawn || !Visual) { Error=TEXT("Missing engineer model or occupied crew position.");return false; }
    auto* Controller=GetWorld()->SpawnActor<AWarSiegeBotController>();Controller->Unit=EWarSiegeUnit::Crew;Controller->Possess(Pawn);
    auto* State=GetWorld()->SpawnActor<AWarPlayerState>();Pawn->SetPlayerState(State);
    State->SetDevelopmentRealm(EWarRealm::Riftbound);State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
    if (!Pawn->SetVisualDefinition(Visual,Error)) return false;
    State->InitializeForPawn(Pawn);Pawn->Unit=EWarSiegeUnit::Crew;
    return Vehicle->BindEngineer(Seat,Pawn);
}
void UWarSiegeEquipmentProof::Tick(float Delta)
{
    if (Finished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds();if (Started<0) Started=Now;
    if (GetWorld()->GetNetMode()==NM_Client) { ObserveClient();return; }
    if (GetWorld()->GetPackage()->GetName()!=TEXT("/Game/Capitals/Siege/AegisCapital_Siege"))
    { Finish(false,TEXT("Requires isolated siege authority world."));return; }
    if (Now-Started<3) return;
    // The observer is a camera, not an escort or a physical obstacle in this fixture.
    for (FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if (auto* Player=It->Get(); Player && !Player->IsA<AWarSiegeBotController>())
            if (APawn* Pawn=Player->GetPawn()) { Pawn->SetActorHiddenInGame(true);Pawn->SetActorEnableCollision(false); }
    if (Step==4)
    {
        Vehicles[0]->Drive(Battlefield->EquipmentDestination(3),150,Delta);
        Vehicles[0]->Operate(true);
        StrikeVerified |= Now-Vehicles[0]->StrikeStarted>.7;
        if (Now-LastMove>6) Finish(StrikeVerified,StrikeVerified
            ? TEXT("Both engines traversed the route; missing escort and dead crew stop movement; repeated arrived commands preserve the ram strike.")
            : TEXT("Repeated escort commands restarted the ram strike."));
        return;
    }
    FString Error;
    if (Step==0)
    {
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld());It;++It) Battlefield=*It;
        if (!Battlefield || Battlefield->EquipmentDefinitions.Num()!=2) { Finish(false,TEXT("Missing convoy bindings."));return; }
        const bool RampDiagnostic=FParse::Param(FCommandLine::Get(),TEXT("WarSiegeEquipmentRampDiagnostic"));
        for (int32 I=0;I<2;++I)
        {
            const FVector Start=Battlefield->Objective(0,RampDiagnostic?1:0)-FVector(I*850,0,0);
            auto* Vehicle=GetWorld()->SpawnActor<AWarSiegeEquipment>(Start,FRotator::ZeroRotator);
            if (!Vehicle || !Vehicle->Initialize(Battlefield->EquipmentDefinitions[I].LoadSynchronous())) { Finish(false,TEXT("Unreviewed or missing equipment."));return; }
            Vehicles.Add(Vehicle);
            for (int32 Seat=0;Seat<2;++Seat) if (!Engineer(Vehicle,Seat,Error)) { Finish(false,Error);return; }
        }
        auto* Ram=Vehicles[0].Get();const FVector Start=Ram->GetActorLocation();
        // Reproduce the reported correction/spawn inside a fully configured ram.
        auto* Trapped=GetWorld()->SpawnActor<AWarSiegeCharacter>(Start+FVector(0,1200,96),FRotator::ZeroRotator);
        auto* RecoveryState=GetWorld()->SpawnActor<AWarPlayerState>();
        if (!Trapped || !RecoveryState) { Finish(false,TEXT("Recovery fixture could not spawn."));return; }
        Trapped->SetPlayerState(RecoveryState);RecoveryState->SetDevelopmentRealm(EWarRealm::Riftbound);
        if (!Trapped->SetVisualDefinition(Battlefield->CrewVisual.LoadSynchronous(),Error)) { Finish(false,Error);return; }
        RecoveryState->InitializeForPawn(Trapped);
        const float Health=RecoveryState->GetAttributes()->GetHealth();
        Trapped->SetActorLocation(Start+FVector(0,0,96),false,nullptr,ETeleportType::TeleportPhysics);
        Ram->Tick(.016f);
        RecoveryVerified=FVector::Dist2D(Trapped->GetActorLocation(),Start)>Ram->Definition->HullExtent.Size2D()
            && !Trapped->IsDead() && RecoveryState->GetAttributes()->GetHealth()==Health;
        Trapped->Destroy();RecoveryState->Destroy();
        if (!RecoveryVerified) { Finish(false,TEXT("A participant trapped inside the ram was not safely relocated."));return; }
        Ram->Drive(Battlefield->Objective(0,1),0,1);StopVerified=Ram->GetActorLocation().Equals(Start);
        auto* Dead=Ram->Engineers[0].Get();Dead->HandleDeath();
        Ram->Drive(Battlefield->Objective(0,1),150,1);DeathVerified=!Ram->HasCrew() && Ram->GetActorLocation().Equals(Start);
        if (auto* Controller=Dead->GetController()) { Controller->UnPossess();Controller->Destroy(); }Dead->Destroy();
        if (!Engineer(Ram,0,Error) || !StopVerified || !DeathVerified) { Finish(false,TEXT("Crew or escort stop invariant failed: ")+Error);return; }
        Step=RampDiagnostic?2:1;LastMove=Now;
    }
    const FVector Goal=Battlefield->EquipmentDestination(Step);
    auto* Ram=Vehicles[0].Get();auto* Catapult=Vehicles[1].Get();
    Catapult->Drive(Ram->TrailingLocation(850),172.5f,Delta);
    if (FVector::Dist2D(Ram->GetActorLocation(),Catapult->GetActorLocation())<1200) Ram->Drive(Goal,150,Delta);
    else Ram->Stop();
    const float Travel=Ram->Travel+Catapult->Travel;
    if (Now>=NextSnapshot)
    {
        NextSnapshot=Now+5;
        UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_EQUIPMENT_POSITION step=%d ram=%s catapult=%s travel=%.1f"),Step,*Ram->GetActorLocation().ToString(),*Catapult->GetActorLocation().ToString(),Travel);
    }
    if (Travel>PreviousTravel+1) { LastMove=Now;PreviousTravel=Travel; }
    if (FVector::Dist2D(Ram->GetActorLocation(),Goal)<(Step==3 ? 5 : 100))
    {
        FWarSiegeState S;S.Phase=EWarSiegePhase::Active;S.MilestoneSeconds.Init(Now,Step+1);Battlefield->ApplyMilestones(S);
        UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_EQUIPMENT_CHECKPOINT=%d travel=%.1f"),Step,Travel);
        if (++Step==4) { Ram->Stop();Catapult->Stop();Ram->Operate(true);LastMove=Now;return; }
    }
    if (Now-LastMove>15 || Now-Started>400) Finish(false,FString::Printf(TEXT("Convoy stalled at step %d. Ram %s; catapult %s."),Step,*Ram->GetActorLocation().ToString(),*Catapult->GetActorLocation().ToString()));
}
void UWarSiegeEquipmentProof::Capture(const FString& Name)
{
    if (Captured.Contains(Name)) return;
    for (const auto& Vehicle:Vehicles)
    {
        UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_CAPTURE %s vehicle=%s transform=%s hidden=%d"),*Name,*Vehicle->GetName(),*Vehicle->GetActorTransform().ToString(),Vehicle->IsHidden());
        TArray<UStaticMeshComponent*> Parts;Vehicle->GetComponents(Parts);
        for (const auto* Part:Parts) UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_PART %s world=%s visible=%d registered=%d"),*Part->GetName(),*Part->GetComponentTransform().ToString(),Part->IsVisible(),Part->IsRegistered());
    }
    const FString Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("SiegeEquipmentProof"));
    IFileManager::Get().MakeDirectory(*Directory,true);
    FScreenshotRequest::RequestScreenshot(FPaths::Combine(Directory,Name+TEXT(".png")),false,false);
    Captured.Add(Name);
}
void UWarSiegeEquipmentProof::ObserveClient()
{
    const double Now=GetWorld()->GetTimeSeconds();
    if (Now-Started>410) { Finish(false,TEXT("Replicated convoy observation timed out."));return; }
    if (!Battlefield) for (TActorIterator<AWarSiegeBattlefield> It(GetWorld());It;++It) Battlefield=*It;
    Vehicles.Reset();
    for (TActorIterator<AWarSiegeEquipment> It(GetWorld());It;++It) if (It->Definition) Vehicles.Add(*It);
    if (Vehicles.Num()!=2 || !Battlefield) return;
    Vehicles.Sort([](const AWarSiegeEquipment& A,const AWarSiegeEquipment& B) { return A.Definition->bBatteringRam && !B.Definition->bBatteringRam; });
    for (const auto& Vehicle:Vehicles)
    {
        if (!Vehicle->HasCrew()) return;
        TArray<UStaticMeshComponent*> Meshes;Vehicle->GetComponents(Meshes);
        if (Meshes.Num()!=Vehicle->Definition->Parts.Num()) return;
        for (auto* Mesh:Meshes) if (!Mesh->GetStaticMesh()) return;
    }
    auto* Player=GetWorld()->GetFirstPlayerController();if (!Player) return;
    if (APawn* Observer=Player->GetPawn()) { Observer->SetActorHiddenInGame(true);Observer->SetActorEnableCollision(false); }
    if (!Camera) { Camera=GetWorld()->SpawnActor<ACameraActor>();Camera->GetCameraComponent()->SetFieldOfView(65); }
    Player->SetViewTarget(Camera);
    auto* Ram=Vehicles[0].Get();const FVector Focus=Ram->GetActorLocation()+FVector(0,0,150);
    FVector Position=Focus+FVector(0,0,1800);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeProofCamera),false);
    for (const auto& Vehicle:Vehicles) { Query.AddIgnoredActor(Vehicle);for (const auto& Crew:Vehicle->Engineers) Query.AddIgnoredActor(Crew); }
    for (const FVector& Offset:{FVector(-1250,1300,1050),FVector(-1250,-1300,1050),FVector(-1000,0,1500)})
    {
        FHitResult Hit;const FVector Candidate=Focus+Offset;
        if (!GetWorld()->LineTraceSingleByChannel(Hit,Focus,Candidate,ECC_Visibility,Query)) { Position=Candidate;break; }
    }
    Camera->SetActorLocationAndRotation(Position,(Focus-Position).Rotation());
    // Synchronous asset resolution can precede the first submitted render frame.
    if (ClientReadyAt<0) ClientReadyAt=Now;
    if (Now-ClientReadyAt<3) return;
    int32 Claims=0;for (const auto& Flag:Battlefield->AttackerStandards) if (IsValid(Flag) && !Flag->IsHidden()) ++Claims;
    if (Claims!=LastClaims) { LastClaims=Claims;ClaimSeenAt=Now; }
    if (Ram->Travel>200 && Claims==0) Capture(TEXT("convoy-start"));
    if (Claims>=2 && Now-ClaimSeenAt>3 && Ram->GetActorLocation().Z<100) Capture(TEXT("checkpoint-owned"));
    if (Ram->GetActorLocation().Z>1500 && Ram->GetActorLocation().Z<3000) Capture(TEXT("convoy-ramp"));
    if (Claims>=4 && Now-ClaimSeenAt>3 && Ram->StrikeStarted>=0)
    {
        Capture(TEXT("gate-owned"));if (ClientFinishedAt<0) ClientFinishedAt=Now;
        if (Now-ClientFinishedAt>2) Finish(Captured.Num()==4,TEXT("Replicated engines, four equipped engineers, ramp motion and attacker ownership rendered on a network client."));
    }
}
