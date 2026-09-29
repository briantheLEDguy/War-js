#include "WarSiegeTraversalProof.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarSiegeBattlefield.h"
#include "WarSiegeGameMode.h"
#include "WarSiegeNavigation.h"
#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Navigation/PathFollowingComponent.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/PlatformMisc.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UWarSiegeTraversalProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarSiegeTraversalProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking"));
#endif
}
bool UWarSiegeTraversalProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarSiegeTraversalProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarSiegeTraversalProof,STATGROUP_Tickables); }
void UWarSiegeTraversalProof::Finish(bool Passed,const FString& Detail)
{
    Finished=true;
    auto Report=MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetStringField(TEXT("detail"),Detail); Report->SetNumberField(TEXT("routesCompleted"),FMath::Max(0,Route));
    Report->SetBoolField(TEXT("traversalReviewGranted"),false); Report->SetBoolField(TEXT("gameplayVerified"),false);
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (int32 I=0;I<Walkers.Num();++I)
    {
        auto Row=MakeShared<FJsonObject>(); Row->SetNumberField(TEXT("walker"),I);
        Row->SetStringField(TEXT("position"),Walkers[I]->GetActorLocation().ToString());
        Row->SetNumberField(TEXT("distanceCm"),Distance[I]); Row->SetBoolField(TEXT("jumped"),Jumped[I]);
        if (Destinations.IsValidIndex(I)) Row->SetStringField(TEXT("destination"),Destinations[I].ToString());
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    Report->SetArrayField(TEXT("walkers"),Rows); FString Json;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("SiegeTraversal.json")));
    UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_TRAVERSAL passed=%d route=%d %s"),Passed,Route,*Detail);
    FPlatformMisc::RequestExitWithStatus(false,Passed ? 0 : 1);
}
bool UWarSiegeTraversalProof::SpawnCrowd(FString& Error)
{
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if (!Nav || Battlefield->TeamSpawns.Num()!=6 || Battlefield->Objectives.Num()!=8 || Battlefield->OptionalObjectives.Num()!=3)
    { Error=TEXT("Missing navigation or siege anchors."); return false; }
    for (int32 I=0;I<12;++I)
    {
        const int32 Team=I/6, Slot=I%6;
        const FVector Seed=Battlefield->TeamSpawns[Team]+FVector((Slot%3-1)*180,(Slot/3)*180,0);
        FNavLocation Ground;
        if (!Nav->ProjectPointToNavigation(Seed,Ground,FVector(100,100,250))) { Error=TEXT("Crowd spawn has no ground."); return false; }
        const TCHAR* Path=Team==0 ? TEXT("/Game/MigrationProof/Visual_civic_sunfire_templar_m") : TEXT("/Game/MigrationProof/Visual_mire_warbrute_m");
        auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,Path);
        if (!Visual || !Visual->ValidateForSpawn(Team==0 ? EWarRealm::Aegis : EWarRealm::Riftbound,Error)) return false;
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
        auto* Pawn=GetWorld()->SpawnActor<AWarSiegeCharacter>(Ground.Location+FVector(0,0,100),FRotator::ZeroRotator,Params);
        if (!Pawn) { Error=TEXT("Colliding crowd spawn."); return false; }
        auto* Controller=GetWorld()->SpawnActor<AWarSiegeBotController>(); Controller->Possess(Pawn);
        auto* State=GetWorld()->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        if (!Pawn->SetVisualDefinition(Visual,Error)) return false;
        State->InitializeForPawn(Pawn);
        Walkers.Add(Pawn); Previous.Add(Pawn->GetActorLocation()); Distance.Add(0); Stalled.Add(0); Jumped.Add(false);
    }
    return true;
}
bool UWarSiegeTraversalProof::StartRoute(FString& Error)
{
    ++Route; if (Route==7) { Finish(true,TEXT("Twelve colliding characters jumped, walked every lower-city objective and sabotage route, and crossed between opposing spawns twice.")); return true; }
    Destinations.Reset(); Stalled.Init(0,12);
    for (int32 I=0;I<Walkers.Num();++I)
    {
        FVector Target=Route<4 ? Battlefield->Objectives[Route] : Route==4 ? Battlefield->OptionalObjectives[0]
            : Battlefield->TeamSpawns[Route==5 ? 1-I/6 : I/6];
        const float Angle=I*2*PI/12;
        FVector Ground;
        if (!WarSiegeNavigation::Approach(Walkers[I],Target,FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*400,Battlefield->ObjectiveRadius,Ground))
        { Error=FString::Printf(TEXT("Walker %d has no clear reachable approach on route %d at %s."),I,Route,*Target.ToString()); return false; }
        Destinations.Add(Ground);
        if (CastChecked<AAIController>(Walkers[I]->GetController())->MoveToLocation(Ground,70,false,true,false,false,nullptr,false)==EPathFollowingRequestResult::Failed)
        { Error=TEXT("Crowd movement request failed."); return false; }
    }
    PhaseAt=GetWorld()->GetTimeSeconds(); UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_TRAVERSAL_ROUTE=%d walkers=12"),Route); return true;
}
void UWarSiegeTraversalProof::Tick(float Delta)
{
    if (Finished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds(); if (StartedAt<0) StartedAt=Now;
    if (GetWorld()->GetNetMode()==NM_Client || GetWorld()->GetPackage()->GetName()!=TEXT("/Game/Capitals/Siege/AegisCapital_Siege"))
    { Finish(false,TEXT("Traversal fixture requires the isolated siege authority world.")); return; }
    FString Error;
    if (Phase==0)
    {
        if (Now-StartedAt<3) return;
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld());It;++It)
        { if (Battlefield) { Finish(false,TEXT("Duplicate battlefield.")); return; } Battlefield=*It; }
        if (!Battlefield || !SpawnCrowd(Error)) { Finish(false,Error.IsEmpty() ? TEXT("Battlefield missing.") : Error); return; }
        Phase=1; PhaseAt=Now; return;
    }
    if (Phase==1)
    {
        if (Now-PhaseAt<1) return;
        for (const auto& Pawn:Walkers) { if (!Pawn->GetCharacterMovement()->IsMovingOnGround()) { Finish(false,TEXT("Spawn did not settle on walkable ground.")); return; } Pawn->Jump(); }
        Phase=2; PhaseAt=Now; return;
    }
    if (Phase==2)
    {
        bool Landed=true;
        for (int32 I=0;I<Walkers.Num();++I)
        { const bool Grounded=Walkers[I]->GetCharacterMovement()->IsMovingOnGround(); Jumped[I]=Jumped[I] || !Grounded; Landed &= Jumped[I] && Grounded; }
        if (Landed) { Phase=3; if (!StartRoute(Error)) Finish(false,Error); }
        else if (Now-PhaseAt>5) Finish(false,TEXT("Crowd jump or landing failed."));
        return;
    }
    bool Arrived=true;
    for (int32 I=0;I<Walkers.Num();++I)
    {
        auto* Pawn=Walkers[I].Get(); const FVector Position=Pawn->GetActorLocation();
        if (!Pawn->IsVisualReady() || Pawn->IsDevelopmentFlying() || Pawn->GetCapsuleComponent()->GetCollisionEnabled()==ECollisionEnabled::NoCollision)
        { Finish(false,TEXT("Traversal lost its visible colliding character.")); return; }
        // The path follower stops within its acceptance radius along a slope;
        // compare feet in 3D rather than imposing a separate flat-floor height.
        const FVector Feet=Position-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        const bool AtGoal=Pawn->GetCharacterMovement()->IsMovingOnGround() && FVector::Dist(Feet,Destinations[I])<110;
        const float Moved=FVector::Dist2D(Position,Previous[I]); Distance[I]+=Moved;
        Stalled[I]=AtGoal || Moved>Delta*5 ? 0 : Stalled[I]+Delta; Previous[I]=Position; Arrived &= AtGoal;
        if (Stalled[I]>8) { Finish(false,FString::Printf(TEXT("Walker %d stalled on route %d at %s."),I,Route,*Position.ToString())); return; }
    }
    if (Arrived) { if (!StartRoute(Error)) Finish(false,Error); }
    else if (Now-PhaseAt>120) Finish(false,TEXT("Crowd route timed out."));
}
