#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarAttributeSet.h"
#include "WarAbilityRuntime.h"
#include "WarAbilityCatalog.h"
#include "WarWarpIdol.h"
#include "WarCombatStatus.h"
#include "WarSiegeNavigation.h"
#include "WarSiegeEquipment.h"
#include "WarSiegeEscort.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Navigation/CrowdFollowingComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

AWarSiegeBotController::AWarSiegeBotController(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UCrowdFollowingComponent>(TEXT("PathFollowingComponent")))
{ bWantsPlayerState = true; PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickInterval = .25f; }
void AWarSiegeBotController::Tick(float Delta)
{
    Super::Tick(Delta);
    auto* Mode = AWarSiegeEncounter::For(this);
    DefaultNavigationFilterClass = WarSiegeNavigation::FilterFor(this);
    auto* BotPawn = Cast<AWarCharacter>(GetPawn()); auto* PS = GetPlayerState<AWarPlayerState>();
    if (!Mode || !Mode->Battlefield || !BotPawn || !PS || BotPawn->IsDead() || !BotPawn->IsVisualReady()) return;
    auto* GS = Mode->SiegeState();
    if (GS->Siege.Phase != EWarSiegePhase::Active || Unit == EWarSiegeUnit::Crew || Unit == EWarSiegeUnit::Commander)
    { if (Unit != EWarSiegeUnit::Crew) StopMovement(); return; }
    FVector Task=Mode->TaskLocation(ObjectiveSide);
    const auto* Commander=Cast<AWarPlayerController>(Leader.Get());
    const auto* Human=Commander ? Cast<AWarCharacter>(Commander->GetPawn()) : nullptr;
    const bool HasLeader=Human && !Human->IsDead();
    const uint8 Order=HasLeader ? Commander->SiegeSquadOrder : 1;
    const bool Optional=Order==3 && !GS->Siege.bOptionalComplete;
    if (Optional) Task=GS->OptionalLocation;
    else if (Order==0 && HasLeader) Task=Human->GetActorLocation();
    else if (Order==2 && HasLeader) Task=Commander->SiegeHoldPosition;
    const FVector Leash=Task;
    AWarCharacter* Enemy = nullptr; AWarCharacter* Injured = BotPawn;
    float LowestHealth = PS->GetAttributes()->GetHealth() / PS->GetAttributes()->GetMaxHealth();
    double Nearest = DBL_MAX; bool PlayerEnemy = false;
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
    {
        const auto* OtherPS = It->GetPlayerState<AWarPlayerState>();
        if (!OtherPS || !Mode->Owns(OtherPS) || It->IsDead() || !It->IsVisualReady()) continue;
        if (OtherPS->GetRealm() == PS->GetRealm() && Mode->IsParticipant(*It)
            && FVector::DistSquared(BotPawn->GetActorLocation(), It->GetActorLocation()) < FMath::Square(2000.f))
        {
            const float Hp = OtherPS->GetAttributes()->GetHealth() / OtherPS->GetAttributes()->GetMaxHealth();
            if (Hp < LowestHealth) { Injured = *It; LowestHealth = Hp; }
        }
        if (FVector::DistSquared(It->GetActorLocation(), Leash) > FMath::Square(2500.f) || !BotPawn->CanAbilityTarget(*It, 2500)) continue;
        const bool Participant = Mode->IsParticipant(*It);
        const double Distance = FVector::DistSquared(BotPawn->GetActorLocation(), It->GetActorLocation());
        if ((Participant && !PlayerEnemy) || (Participant == PlayerEnemy && Distance < Nearest))
        { Enemy = *It; Nearest = Distance; PlayerEnemy = Participant; }
    }
    const float Hp = PS->GetAttributes()->GetHealth() / PS->GetAttributes()->GetMaxHealth();
    const bool Hazard = GS->HazardUntil > GetWorld()->GetTimeSeconds()
        && FVector::Dist2D(BotPawn->GetActorLocation(), GS->HazardLocation) < 600;
    const auto Decision = WarSiege::Decide(Hazard, bRecovering, Hp, Enemy != nullptr,
        false, HasLeader && Order==0);
    bRecovering = Decision == EWarSiegeDecision::Recover;
    if (Decision != LastDecision)
    { UE_LOG(LogTemp, Verbose, TEXT("WAR_SIEGE_BOT %s decision=%d"), *PS->GetPlayerName(), int32(Decision)); LastDecision = Decision; }
    auto* Catalog = GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    auto* Runtime = PS->GetClassAbilities(); FString Error;
    const bool Escort=Unit==EWarSiegeUnit::Participant && PS->GetRealm()==EWarRealm::Riftbound && Order==1
        && GS->Siege.RulesVersion==2 && GS->Siege.Stage==0 && GS->Siege.Objective>0
        && EscortSeat>=0 && EscortSeat<18 && Mode->ConvoyVehicles().Num()==2;
    const bool ClearVehicle=Escort && !WarSiegeNavigation::ConvoyPositionClear(BotPawn,Mode);
    const auto MoveEscort=[&](const FVector& Anchor,const FVector& Offset,bool Formation)
    {
        FVector Ground;
        if (!WarSiegeNavigation::ConvoyApproach(BotPawn,Anchor,Offset,Mode->Battlefield->ObjectiveRadius,Mode,Ground,Formation))
        { StopMovement();return; }
        if (GetMoveStatus()!=EPathFollowingStatus::Moving || FVector::DistSquared(LastMoveGoal,Ground)>FMath::Square(35.f))
        { MoveToLocation(Ground,25,false);LastMoveGoal=Ground; }
    };
    const auto EscortOffset=[&]() { return WarSiegeEscort::Offset(EscortSeat,Mode->ConvoyVehicles()[0]->GetActorRotation().Yaw); };
    if (ClearVehicle && Runtime->IsStationaryCast()) Runtime->UpdateMovementIntent(true);
    if (ClearVehicle && !Runtime->OwnsMovement()) { MoveEscort(Mode->TaskLocation(),EscortOffset(),true);return; }
    const auto Kit = Catalog ? Catalog->Kit(BotPawn->GetCareerId()) : TArray<const FWarAbilityDefinition*>();
    const auto TryCombatAbility=[&](FName Id,AActor* Aim) {
        const auto* A=Catalog ? Catalog->Find(Id,BotPawn->GetCareerId()) : nullptr;
        if (A && Runtime->CanPrepareStationaryCast(*A,Aim,Error))
        { StopMovement(); BotPawn->GetCharacterMovement()->StopMovementImmediately(); Runtime->UpdateMovementIntent(false); }
        return Runtime->TryActivate(Id,Aim,Error);
    };
    if (Decision == EWarSiegeDecision::Evade)
    {
        ClearFocus(EAIFocusPriority::Gameplay);
        FVector Away = (BotPawn->GetActorLocation() - GS->HazardLocation).GetSafeNormal2D();
        if (Away.IsNearlyZero()) Away = FVector::ForwardVector;
        MoveToLocation(GS->HazardLocation + Away * 850, 50); return;
    }
    // Defensive and healing choices still pass ordinary class resource/cooldown/animation validation.
    for (const auto* A : Kit)
    {
        bool Heal = false, Defense = false;
        for (const auto& E : A->Effects)
        { Heal |= E.Kind == TEXT("heal"); Defense |= E.Kind == TEXT("player_status") && (E.StatusKind == TEXT("shield") || E.StatusKind == TEXT("guard")); }
        if ((Heal && ((CombatRole == EWarSiegeRole::Healer && LowestHealth < .85f) || Hp < .6f)) || (Defense && Hp < .6f))
            if (TryCombatAbility(A->Id, Heal && CombatRole == EWarSiegeRole::Healer ? Injured : BotPawn)) break;
    }
    if (Runtime->IsStationaryCast() || Runtime->OwnsMovement()) { StopMovement(); return; }
    if (Decision == EWarSiegeDecision::Recover)
    {
        FVector Help = HasLeader ? Human->GetActorLocation() : Mode->Battlefield->TeamSpawns[GS->Siege.Stage * 2 + (PS->GetRealm() == EWarRealm::Aegis ? 0 : 1)];
        for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
            if (const auto* Ally = Cast<AWarSiegeBotController>(It->GetController()); Ally && Ally->CombatRole == EWarSiegeRole::Healer
                && !It->IsDead() && It->GetPlayerState<AWarPlayerState>()->GetRealm() == PS->GetRealm()
                && FVector::Dist2D(It->GetActorLocation(), BotPawn->GetActorLocation()) < 2000) { Help = It->GetActorLocation(); break; }
        MoveToLocation(Help, 250); return;
    }
    if (Decision == EWarSiegeDecision::Combat && Enemy)
    {
        SetFocus(Enemy);
        bool Activated = false;
        if (BotPawn->GetCareerId() == TEXT("void_magister") && Nearest < FMath::Square(1000.f))
        {
            const bool HasIdol = AWarWarpIdol::HasFor(BotPawn);
            if (!HasIdol) Activated = TryCombatAbility(TEXT("void_magister.summon_idol"), BotPawn);
            else if (const auto* Status = UWarCombatStatus::On(BotPawn); Status && !Status->Has(TEXT("empower")))
                Activated = TryCombatAbility(TEXT("void_magister.feed_the_idol"), BotPawn);
        }
        for (const auto* A : Kit)
        {
            if (Activated) break;
            bool Offensive = false; for (const auto& E : A->Effects) Offensive |= E.Kind == TEXT("damage") || E.Kind == TEXT("status");
            if (Offensive && TryCombatAbility(A->Id, Enemy)) { Activated = true; break; }
        }
        if (Runtime->IsStationaryCast() || Runtime->OwnsMovement()) StopMovement();
        else
        {
            BotPawn->RequestTargetStrike(Enemy);
            // When every class action is unavailable, close to basic-strike range.
            // A role-based ranged stopping distance can strand melee damage kits.
            if (Escort)
            {
                const bool Formation=EscortSeat%3==0;
                const FVector Offset=Formation ? EscortOffset()
                    : (Enemy->GetActorLocation()-Mode->TaskLocation()).GetSafeNormal2D()*225;
                MoveEscort(Formation ? Mode->TaskLocation() : Enemy->GetActorLocation(),Offset,Formation);
            }
            else if (Unit != EWarSiegeUnit::Emplacement) MoveToActor(Enemy,100,false);
        }
        return;
    }
    ClearFocus(EAIFocusPriority::Gameplay);
    if (Unit == EWarSiegeUnit::Emplacement) { StopMovement(); return; }
    if (Escort) { MoveEscort(Mode->TaskLocation(),EscortOffset(),true);return; }
    if (StalledSeconds<0)
    {
        StalledSeconds=FMath::Min(0.,StalledSeconds+Delta);
        if (GetMoveStatus()==EPathFollowingStatus::Moving && StalledSeconds<0) return;
        StalledSeconds=0;
    }
    // Offset squad members without pulling them outside objective participation radius.
    const float Angle = float(GetUniqueID() % 6) * PI / 3;
    const FVector Offset(FMath::Cos(Angle) * 400, FMath::Sin(Angle) * 400, 0);
    const FVector Goal=Task;
    if (FVector::DistSquared(BotPawn->GetActorLocation(), PreviousLocation) < 25 && FVector::Dist2D(BotPawn->GetActorLocation(), Goal) > 650)
        StalledSeconds += Delta;
    else StalledSeconds = 0;
    PreviousLocation = BotPawn->GetActorLocation();
    if (StalledSeconds >= 5)
    {
        StopMovement(); StalledSeconds = 0;
        UE_LOG(LogTemp, Warning, TEXT("WAR_SIEGE_ROUTE_STALL bot=%s position=%s goal=%s"), *PS->GetPlayerName(),*BotPawn->GetActorLocation().ToString(),*Goal.ToString());
        FVector Detour;
        const float Sign=(FMath::FloorToInt(GetWorld()->GetTimeSeconds()/5)+GetUniqueID())%2 ? 1.f : -1.f;
        if (WarSiegeNavigation::Detour(BotPawn,Goal,Sign,Detour)
            && MoveToLocation(Detour,50,false)!=EPathFollowingRequestResult::Failed)
        { LastMoveGoal=Detour;StalledSeconds=-3;return; }
    }
    FVector Destination;
    if (WarSiegeNavigation::Approach(BotPawn,Goal,Offset,Order==0 ? 600.f : Mode->Battlefield->ObjectiveRadius,Destination))
    {
        // Do not restart a valid path every AI tick; that starves crowd movement.
        if (GetMoveStatus()!=EPathFollowingStatus::Moving || FVector::DistSquared(Destination,LastMoveGoal)>FMath::Square(150.f))
        {
            const auto Result=MoveToLocation(Destination,70,false);
            LastMoveGoal=Destination;
            if (Result==EPathFollowingRequestResult::Failed) UE_LOG(LogTemp,Warning,TEXT("WAR_SIEGE_MOVE_FAILED %s"),*PS->GetPlayerName());
        }
    }
    else StopMovement();
}
