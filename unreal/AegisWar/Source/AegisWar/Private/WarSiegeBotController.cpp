#include "WarSiegeGameMode.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarAbilityRuntime.h"
#include "WarAbilityCatalog.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"

AWarSiegeBotController::AWarSiegeBotController()
{ bWantsPlayerState = true; PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickInterval = .25f; }
void AWarSiegeBotController::Tick(float Delta)
{
    Super::Tick(Delta);
    auto* Mode = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>();
    auto* BotPawn = Cast<AWarCharacter>(GetPawn()); auto* PS = GetPlayerState<AWarPlayerState>();
    if (!Mode || !Mode->Battlefield || !BotPawn || !PS || BotPawn->IsDead() || !BotPawn->IsVisualReady()) return;
    auto* GS = Mode->SiegeState();
    if (GS->Siege.Phase != EWarSiegePhase::Active || Unit == EWarSiegeUnit::Crew || Unit == EWarSiegeUnit::Commander)
    { if (Unit != EWarSiegeUnit::Crew) StopMovement(); return; }
    FVector Task = Mode->TaskLocation();
    const auto* Human = Leader.IsValid() ? Cast<AWarCharacter>(Leader->GetPawn()) : nullptr;
    const bool HasLeader = Human && !Human->IsDead();
    const FVector Leash = HasLeader ? Human->GetActorLocation() : Task;
    AWarCharacter* Enemy = nullptr; AWarCharacter* Injured = BotPawn;
    float LowestHealth = PS->GetAttributes()->GetHealth() / PS->GetAttributes()->GetMaxHealth();
    double Nearest = DBL_MAX; bool PlayerEnemy = false;
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
    {
        const auto* OtherPS = It->GetPlayerState<AWarPlayerState>();
        if (!OtherPS || It->IsDead() || !It->IsVisualReady()) continue;
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
        FVector::Dist2D(BotPawn->GetActorLocation(), Task) < 1800, HasLeader);
    bRecovering = Decision == EWarSiegeDecision::Recover;
    if (Decision != LastDecision)
    { UE_LOG(LogTemp, Verbose, TEXT("WAR_SIEGE_BOT %s decision=%d"), *PS->GetPlayerName(), int32(Decision)); LastDecision = Decision; }
    auto* Catalog = GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    auto* Runtime = PS->GetClassAbilities(); FString Error;
    const auto Kit = Catalog ? Catalog->Kit(BotPawn->GetCareerId()) : TArray<const FWarAbilityDefinition*>();
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
            if (Runtime->TryActivate(A->Id, Heal && CombatRole == EWarSiegeRole::Healer ? Injured : BotPawn, Error)) break;
    }
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
        for (const auto* A : Kit)
        {
            bool Offensive = false; for (const auto& E : A->Effects) Offensive |= E.Kind == TEXT("damage") || E.Kind == TEXT("status");
            if (Offensive && Runtime->TryActivate(A->Id, Enemy, Error)) { Activated = true; break; }
        }
        if (Activated || Runtime->IsBusy() || BotPawn->IsActionPlaying()) StopMovement();
        else
        {
            BotPawn->RequestTargetStrike(Enemy);
            // When every class action is unavailable, close to basic-strike range.
            // A role-based ranged stopping distance can strand melee damage kits.
            if (Unit != EWarSiegeUnit::Emplacement) MoveToActor(Enemy, 100, false);
        }
        return;
    }
    ClearFocus(EAIFocusPriority::Gameplay);
    if (Unit == EWarSiegeUnit::Emplacement) { StopMovement(); return; }
    // Offset squad members without pulling them outside objective participation radius.
    const float Angle = float(GetUniqueID() % 6) * PI / 3;
    const FVector Offset(FMath::Cos(Angle) * 250, FMath::Sin(Angle) * 250, 0);
    MoveToLocation((Decision == EWarSiegeDecision::Follow && HasLeader ? Human->GetActorLocation() : Task) + Offset, 100);
}
