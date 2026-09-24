#include "WarSiegeGameMode.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCharacterVisualDefinition.h"
#include "WarCombatStatus.h"
#include "WarAbilityRuntime.h"
#include "WarWorldEditSubsystem.h"
#include "WarGmRules.h"
#include "WarRuntimeSettings.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "WarSiegeHud.h"
#include "AbilitySystemComponent.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"

void AWarSiegeCharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{ Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(AWarSiegeCharacter, Unit); }
void AWarSiegeCharacter::Tick(float Delta)
{ Super::Tick(Delta); if (Unit == EWarSiegeUnit::Crew) GetCharacterMovement()->MaxWalkSpeed = CrewMoveSpeed; }
AWarSiegeGameMode::AWarSiegeGameMode()
{
    GameStateClass = AWarSiegeGameState::StaticClass(); HUDClass = AWarSiegeHud::StaticClass();
    PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickInterval = .05f;
}
AWarSiegeGameState* AWarSiegeGameMode::SiegeState() const { return GetGameState<AWarSiegeGameState>(); }
bool AWarSiegeGameMode::Authorized(AWarPlayerController* Gm, FString& Error) const
{
    // Local siege recovery must work while the GM is dead or a failed spawn has no pawn.
    // Keep the same standalone-only development policy; no network role is inferred.
    if (!HasAuthority() || !Gm || !Gm->HasAuthority() || !Gm->IsLocalController() || Gm->GetWorld() != GetWorld()
        || UWorld::RemovePIEPrefix(GetWorld()->GetOutermost()->GetName()) != TEXT("/Game/Capitals/Siege/AegisCapital_Siege")
        || !WarGmRules::AllowsDevelopmentSession(UE_BUILD_SHIPPING != 0, GetNetMode(), GetWorld()->WorldType,
            GetDefault<UWarRuntimeSettings>()->bEnableLocalDevelopmentGM, FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM"))))
    { Error = TEXT("Siege controls require authorized development GM access."); return false; }
    return true;
}
bool AWarSiegeGameMode::Launch(AWarPlayerController* Gm, int32 Capacity, int32 Seed, FString& Error)
{
    if (!Authorized(Gm, Error)) return false;
    auto* GS = SiegeState();
    if (!GS || !WarSiege::ValidCapacity(Capacity) || GS->Siege.Phase == EWarSiegePhase::Active || GS->Siege.Phase == EWarSiegePhase::Transition)
    { Error = TEXT("Choose 6, 12 or 18 slots and reset the previous siege before launching."); return false; }
    Battlefield = nullptr;
    for (TActorIterator<AWarSiegeBattlefield> It(GetWorld()); It; ++It)
    {
        if (Battlefield) { Error = TEXT("The siege map contains duplicate battlefield definitions."); return false; }
        Battlefield = *It;
    }
    if (!Battlefield || !Battlefield->Validate(Error))
    { if (!Battlefield) Error = TEXT("Open an authored siege map with a validated battlefield definition."); GS->Status = Error; return false; }
    int32 HumanCounts[2] = {};
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        const auto* PS = It->Get()->GetPlayerState<AWarPlayerState>();
        if (PS && PS->GetRealm() != EWarRealm::None) ++HumanCounts[PS->GetRealm() == EWarRealm::Aegis ? 0 : 1];
    }
    if (HumanCounts[0] > Capacity || HumanCounts[1] > Capacity)
    { Error = TEXT("Connected realm population exceeds the selected capacity."); return false; }
    ClearUnits(true); Random.Initialize(Seed); StartedStage = -1;
    WarSiege::Start(GS->Siege, Capacity); GS->NextWaveAt = GetWorld()->GetTimeSeconds();
    StageStarted();
    if (GS->Siege.Phase == EWarSiegePhase::Waiting) { Error = GS->Status; return false; }
    Wave();
    if (GS->Siege.Phase == EWarSiegePhase::Waiting) { Error = GS->Status; return false; }
    Publish();
    UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_START capacity=%d seed=%d definition=1"), Capacity, Seed);
    return true;
}
bool AWarSiegeGameMode::ResetSiege(AWarPlayerController* Gm, FString& Error)
{
    if (!Authorized(Gm, Error)) return false;
    ClearUnits(true); StartedStage = -1;
    auto* GS = SiegeState(); GS->Siege = {}; GS->Status = TEXT("Siege reset; awaiting GM launch."); GS->RosterLabels.Reset();
    GS->HazardUntil = 0; GS->CommanderAction.Reset();
    if (Battlefield) Battlefield->ApplyMilestones(GS->Siege);
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PS = It->Get()->GetPlayerState<AWarPlayerState>()) PS->SetSiegeNormalized(false);
    GS->ForceNetUpdate(); return true;
}
void AWarSiegeGameMode::FailMatch(const FString& Error)
{
    ClearUnits(true); auto* GS = SiegeState(); GS->Siege.Phase = EWarSiegePhase::Waiting; GS->Status = Error;
    GS->HazardUntil = 0; GS->CommanderAction.Reset(); GS->RosterLabels.Reset();
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PS = It->Get()->GetPlayerState<AWarPlayerState>()) PS->SetSiegeNormalized(false);
    GS->ForceNetUpdate(); UE_LOG(LogTemp, Error, TEXT("WAR_SIEGE_BLOCKED %s"), *Error);
}
void AWarSiegeGameMode::HandleStartingNewPlayer_Implementation(APlayerController* Player)
{
    // Existing frontend performs realm/character validation. Admission restrictions remain inherited.
    Super::HandleStartingNewPlayer_Implementation(Player);
}
APawn* AWarSiegeGameMode::SpawnDefaultPawnAtTransform_Implementation(AController* Player, const FTransform& Transform)
{
    auto* Bot = Cast<AWarSiegeBotController>(Player);
    if (!Bot) return Super::SpawnDefaultPawnAtTransform_Implementation(Player, Transform);
    FString Error;
    auto* PS = Bot->GetPlayerState<AWarPlayerState>();
    if (!PS || !Bot->Visual || !Bot->Visual->ValidateForSpawn(PS->GetRealm(), Error)) return nullptr;
    auto* Pawn = GetWorld()->SpawnActorDeferred<AWarSiegeCharacter>(AWarSiegeCharacter::StaticClass(), Transform,
        Player, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding);
    if (!Pawn) return nullptr;
    Pawn->Unit = Bot->Unit;
    if (!Pawn->SetVisualDefinition(Bot->Visual, Error)) { Pawn->Destroy(); return nullptr; }
    Pawn->FinishSpawning(Transform); return Pawn;
}
void AWarSiegeGameMode::RestartPlayer(AController* Player)
{
    if (!Player) return;
    const auto* GS = SiegeState();
    if (!Battlefield || !GS || GS->Siege.Phase == EWarSiegePhase::Waiting) { Super::RestartPlayer(Player); return; }
    // Only Wave admits humans during a siege; frontend entry cannot bypass slot limits.
    if (!Cast<AWarSiegeBotController>(Player)) return;
}
AWarSiegeBotController* AWarSiegeGameMode::SpawnUnit(EWarRealm Realm, EWarSiegeRole CombatRole, EWarSiegeUnit Unit,
    UWarCharacterVisualDefinition* Visual, const FVector& Position)
{
    auto* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    FNavLocation Ground;
    if (!Navigation || !Navigation->ProjectPointToNavigation(Position, Ground, FVector(150,150,500))) return nullptr;
    auto* Controller = GetWorld()->SpawnActor<AWarSiegeBotController>();
    if (!Controller) return nullptr;
    auto* PS = Controller->GetPlayerState<AWarPlayerState>();
    if (!PS) { Controller->Destroy(); return nullptr; }
    Controller->CombatRole = CombatRole; Controller->Unit = Unit; Controller->Visual = Visual;
    PS->SetDevelopmentRealm(Realm); PS->SetCurrentZoneTrusted(TEXT("aegis_capital"));
    PS->SetPlayerName(Unit == EWarSiegeUnit::Participant ? FString::Printf(TEXT("[Bot] %s %d"), *Visual->ClassId.ToString(), Units.Num() + 1)
        : Unit == EWarSiegeUnit::Commander ? TEXT("Bastion Commander") : Unit == EWarSiegeUnit::Crew ? TEXT("Riftbound Breach Engineer") : TEXT("Bastion Garrison"));
    RestartPlayerAtTransform(Controller, FTransform(FRotator::ZeroRotator, Ground.Location + FVector(0,0,100)));
    if (!Controller->GetPawn()) { if (PS) PS->Destroy(); Controller->Destroy(); return nullptr; }
    PS->SetSiegeNormalized(true);
    float Hp = 2000;
    if (Unit == EWarSiegeUnit::Commander) Hp = Battlefield->ReferenceDamagePerSecond * 4 * 180 * WarSiege::HealthScale(SiegeState()->Siege.Capacity);
    else if (Unit == EWarSiegeUnit::Crew) Hp = Battlefield->ReferenceDamagePerSecond * 2 * 20 * WarSiege::HealthScale(SiegeState()->Siege.Capacity);
    else if (Unit != EWarSiegeUnit::Participant) Hp = 1000;
    PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(), Hp);
    PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), Hp);
    Units.Add(Controller); return Controller;
}
void AWarSiegeGameMode::ClearUnits(bool Participants)
{
    for (auto& Weak : Units) if (auto* Bot = Weak.Get(); Bot && (Participants || Bot->Unit != EWarSiegeUnit::Participant))
    {
        if (Bot->GetPawn()) Bot->GetPawn()->Destroy();
        if (Bot->PlayerState) Bot->PlayerState->Destroy();
        Bot->Destroy();
    }
    Units.RemoveAll([](const auto& U) { return !U.IsValid(); }); Crew.Reset(); Commander.Reset();
}
void AWarSiegeGameMode::RespawnAfterDeath(AWarCharacter* Character)
{
    if (!Character || !HasAuthority()) return;
    if (!SiegeState() || SiegeState()->Siege.Phase == EWarSiegePhase::Waiting) { Super::RespawnAfterDeath(Character); return; }
    auto* Controller = Character->GetController();
    if (!Controller) return;
    if (auto* Bot = Cast<AWarSiegeBotController>(Controller))
    {
        if (Bot->Unit == EWarSiegeUnit::Crew)
        { CrewAt = GetWorld()->GetTimeSeconds() + WarSiege::CrewReplacementSeconds; SiegeState()->Siege.Progress = 0; }
        // Retain commander controller until Tick consumes its death exactly once.
        if (Bot->Unit == EWarSiegeUnit::Commander) { Bot->StopMovement(); return; }
        Controller->UnPossess();
        if (Bot->PlayerState) Bot->PlayerState->Destroy();
        Bot->Destroy();
    }
    else Controller->UnPossess();
    Character->SetLifeSpan(5);
    UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_DEATH stage=%d"), SiegeState()->Siege.Stage);
}
bool AWarSiegeGameMode::IsParticipant(const AWarCharacter* Pawn) const
{
    const auto* SiegePawn = Cast<AWarSiegeCharacter>(Pawn);
    return Pawn && (!SiegePawn || SiegePawn->Unit == EWarSiegeUnit::Participant)
        && Pawn->GetPlayerState<AWarPlayerState>() && Pawn->GetPlayerState<AWarPlayerState>()->IsSiegeNormalized();
}
bool AWarSiegeGameMode::IsProtected(const AActor* Actor) const
{
    const auto* GS = SiegeState();
    if (!GS || GS->Siege.Phase != EWarSiegePhase::Active) return true;
    if (!Battlefield || !Actor) return true;
    for (int32 Side = 0; Side < 2; ++Side)
        if (FVector::DistSquared(Actor->GetActorLocation(), Battlefield->TeamSpawns[GS->Siege.Stage * 2 + Side]) < FMath::Square(750.f)) return true;
    return false;
}
FVector AWarSiegeGameMode::TaskLocation() const
{
    const auto& S = SiegeState()->Siege;
    if (WarSiege::IsEscort(S) && Crew.IsValid() && Crew->GetPawn()) return Crew->GetPawn()->GetActorLocation();
    return Battlefield ? Battlefield->Objective(S.Stage, S.Objective) : FVector::ZeroVector;
}
void AWarSiegeGameMode::Wave()
{
    auto* GS = SiegeState(); if (!Battlefield || GS->Siege.Phase != EWarSiegePhase::Active) return;
    Units.RemoveAll([](const auto& U) { return !U.IsValid(); });
    for (EWarRealm Realm : { EWarRealm::Aegis, EWarRealm::Riftbound })
    {
        TArray<APlayerController*> Humans; TArray<AWarSiegeBotController*> Bots;
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (auto* PS = It->Get()->GetPlayerState<AWarPlayerState>(); PS && PS->GetRealm() == Realm) Humans.Add(It->Get());
        for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && B->Unit == EWarSiegeUnit::Participant
            && B->GetPlayerState<AWarPlayerState>()->GetRealm() == Realm) Bots.Add(B);
        const int32 Admitted = FMath::Min(Humans.Num(), GS->Siege.Capacity);
        while (Bots.Num() > GS->Siege.Capacity - Admitted)
        {
            auto* B = Bots.Pop(); if (B->GetPawn()) B->GetPawn()->Destroy();
            if (B->PlayerState) B->PlayerState->Destroy(); B->Destroy();
        }
        const FVector Spawn = Battlefield->TeamSpawns[GS->Siege.Stage * 2 + (Realm == EWarRealm::Aegis ? 0 : 1)];
        for (int32 I = 0; I < Admitted; ++I)
        {
            auto* PC = Humans[I]; auto* PS = PC->GetPlayerState<AWarPlayerState>();
            PS->SetCurrentZoneTrusted(TEXT("aegis_capital"));
            const bool Respawning = !PC->GetPawn();
            if (Respawning) RestartPlayerAtTransform(PC, FTransform(FRotator::ZeroRotator, Spawn + FVector((I % 6) * 110, (I / 6) * 110, 100)));
            if (PC->GetPawn() && (Respawning || !PS->IsSiegeNormalized())) PS->SetSiegeNormalized(true);
        }
        int32 Tanks = 0, Healers = 0;
        for (auto* PC : Humans) if (auto* Pawn = Cast<AWarCharacter>(PC->GetPawn()))
            for (const auto& E : Battlefield->Roster) if (E.Realm == Realm && E.Visual.LoadSynchronous()->ClassId == Pawn->GetCareerId())
            { Tanks += E.CombatRole == EWarSiegeRole::Tank; Healers += E.CombatRole == EWarSiegeRole::Healer; break; }
        for (auto* B : Bots) { Tanks += B->CombatRole == EWarSiegeRole::Tank; Healers += B->CombatRole == EWarSiegeRole::Healer; }
        for (int32 I = Admitted + Bots.Num(); I < GS->Siege.Capacity; ++I)
        {
            const auto CombatRole = WarSiege::MissingRole(GS->Siege.Capacity, Tanks, Healers);
            TArray<const FWarSiegeRosterEntry*> Choices;
            for (const auto& E : Battlefield->Roster) if (E.Realm == Realm && E.CombatRole == CombatRole) Choices.Add(&E);
            if (Choices.IsEmpty()) break;
            const auto* E = Choices[Random.RandRange(0, Choices.Num() - 1)];
            if (SpawnUnit(Realm, CombatRole, EWarSiegeUnit::Participant, E->Visual.LoadSynchronous(), Spawn + FVector((I % 6) * 110, (I / 6) * 110, 0)))
            { Tanks += CombatRole == EWarSiegeRole::Tank; Healers += CombatRole == EWarSiegeRole::Healer; }
            else { FailMatch(TEXT("Bot spawn failed; check model and spawn clearance, then relaunch.")); return; }
        }
    }
    AssignSquads(); GS->NextWaveAt = GetWorld()->GetTimeSeconds() + WarSiege::WaveSeconds;
}
void AWarSiegeGameMode::AssignSquads()
{
    TMap<AController*, int32> Counts;
    for (auto& Weak : Units) if (auto* B = Weak.Get(); B && B->Unit == EWarSiegeUnit::Participant)
    {
        B->Leader.Reset();
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        {
            auto* PC = It->Get(); auto* PS = PC->GetPlayerState<AWarPlayerState>();
            if (!PC->GetPawn() || !PS || PS->GetRealm() != B->GetPlayerState<AWarPlayerState>()->GetRealm() || Counts.FindRef(PC) >= 5) continue;
            if (!B->Leader.IsValid() || Counts.FindRef(PC) < Counts.FindRef(B->Leader.Get())) B->Leader = PC;
        }
        if (B->Leader.IsValid()) ++Counts.FindOrAdd(B->Leader.Get());
    }
}
void AWarSiegeGameMode::StageStarted()
{
    auto* GS = SiegeState(); ClearUnits(false); StartedStage = GS->Siege.Stage;
    CrewAt = 0; CommanderDamageAt = -100; CommanderEngagedAt = GetWorld()->GetTimeSeconds();
    CommanderActionAt = CommanderEngagedAt + 6; CommanderReleaseAt = 0; CommanderSequence = 0;
    GS->HazardUntil = 0; GS->CommanderAction.Reset(); ReinforcementAt = CommanderEngagedAt;
    // Relocate humans at stage boundaries; corpses never cross into the next stage.
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = It->Get(); if (APawn* Pawn = PC->GetPawn()) { PC->UnPossess(); Pawn->Destroy(); }
    }
    for (auto& Weak : Units) if (auto* B = Weak.Get())
    { if (B->GetPawn()) B->GetPawn()->Destroy(); if (B->PlayerState) B->PlayerState->Destroy(); B->Destroy(); }
    Units.Reset(); GS->NextWaveAt = GetWorld()->GetTimeSeconds();
    if (StartedStage == 2)
    {
        Commander = SpawnUnit(EWarRealm::Aegis, EWarSiegeRole::Tank, EWarSiegeUnit::Commander, Battlefield->CommanderVisual.LoadSynchronous(), Battlefield->Objective(2,0));
        if (!Commander.IsValid()) { FailMatch(TEXT("Commander spawn failed; repair model or spawn clearance and relaunch.")); return; }
    }
    if (StartedStage == 0)
        if (!SpawnUnit(EWarRealm::Aegis, EWarSiegeRole::Damage, EWarSiegeUnit::Emplacement, Battlefield->GuardVisual.LoadSynchronous(), Battlefield->OptionalObjectives[0]))
        { FailMatch(TEXT("Emplacement crew spawn failed; repair content and relaunch.")); return; }
    UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_STAGE stage=%d"), StartedStage);
}
void AWarSiegeGameMode::CommanderDamaged() { CommanderDamageAt = GetWorld()->GetTimeSeconds(); }
void AWarSiegeGameMode::Encounters(float Delta)
{
    auto* GS = SiegeState(); auto& S = GS->Siege; const double Now = GetWorld()->GetTimeSeconds();
    const bool NeedCrew = S.Stage < 2 && (WarSiege::IsEscort(S) || S.Objective == WarSiege::FinalObjective(S.Stage));
    if (NeedCrew && !Crew.IsValid() && Now >= CrewAt)
    {
        Crew = SpawnUnit(EWarRealm::Riftbound, EWarSiegeRole::Damage, EWarSiegeUnit::Crew, Battlefield->CrewVisual.LoadSynchronous(),
            Battlefield->Objective(S.Stage, S.Stage == 0 ? S.Objective - 1 : S.Objective));
        if (!Crew.IsValid()) { FailMatch(TEXT("Breach crew spawn failed; repair content and relaunch.")); return; }
    }
    if (NeedCrew && !WarSiege::IsEscort(S) && Crew.IsValid()) Crew->MoveToLocation(Battlefield->Objective(S.Stage, S.Objective), 100);
    int32 LivingGuards = 0;
    for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && (B->Unit == EWarSiegeUnit::Guard || B->Unit == EWarSiegeUnit::Emplacement)) ++LivingGuards;
    const int32 WaveSize = WarSiege::Reinforcements(S.Capacity, S.bOptionalComplete && S.Stage > 0);
    if (Now >= ReinforcementAt && S.Stage < 2)
    {
        for (int32 I = 0; I < FMath::Min(WaveSize, WaveSize * 2 - LivingGuards); ++I)
            if (!SpawnUnit(EWarRealm::Aegis, EWarSiegeRole::Damage, EWarSiegeUnit::Guard, Battlefield->GuardVisual.LoadSynchronous(),
                TaskLocation() + FVector(900 + I * 120, 900, 0)))
            { FailMatch(TEXT("Garrison spawn failed; repair encounter spawn clearance and relaunch.")); return; }
        ReinforcementAt = Now + 60;
    }
    if (S.Stage == 0 && S.bOptionalComplete)
        for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && B->Unit == EWarSiegeUnit::Emplacement)
        { if (B->GetPawn()) B->GetPawn()->Destroy(); if (B->PlayerState) B->PlayerState->Destroy(); B->Destroy(); }
    if (S.Stage != 2 || !Commander.IsValid()) return;
    auto* Boss = Cast<AWarCharacter>(Commander->GetPawn());
    if (!Boss || Boss->IsDead()) return;
    AWarCharacter* Victim = nullptr;
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
        if (IsParticipant(*It) && !It->IsDead() && Boss->CanAbilityTarget(*It, 2500))
        { Victim = *It; CommanderEngagedAt = Now; break; }
    if (!Victim && Now - CommanderEngagedAt >= WarSiege::CommanderResetSeconds)
    {
        auto* PS = Boss->GetPlayerState<AWarPlayerState>();
        PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), PS->GetAttributes()->GetMaxHealth());
        if (auto* Status = UWarCombatStatus::On(Boss)) Status->Clear();
        for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && B->Unit == EWarSiegeUnit::Guard)
        { if (B->GetPawn()) B->GetPawn()->Destroy(); if (B->PlayerState) B->PlayerState->Destroy(); B->Destroy(); }
        GS->CommanderAction.Reset(); GS->HazardUntil = 0; CommanderReleaseAt = 0;
        CommanderDamageAt = -100; CommanderActionAt = Now + 6; CommanderEngagedAt = Now;
        UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_COMMANDER_RESET"));
    }
    if (CommanderReleaseAt > 0)
    {
        const auto* Status = UWarCombatStatus::On(Boss);
        bCommanderInterrupted |= CommanderSequence % 3 == 2 && Status && (Status->Has(TEXT("stagger")) || Status->Has(TEXT("silence")));
        if (Now < CommanderReleaseAt) return;
        const int32 Action = CommanderSequence % 3;
        if (Action == 2 && !bCommanderInterrupted)
        {
            for (int32 I = 0; I < FMath::Min(WaveSize, WaveSize * 2 - LivingGuards); ++I)
                if (!SpawnUnit(EWarRealm::Aegis, EWarSiegeRole::Damage, EWarSiegeUnit::Guard, Battlefield->GuardVisual.LoadSynchronous(), Boss->GetActorLocation() + FVector(500,I*120,0)))
                { FailMatch(TEXT("Rally spawn failed; repair encounter spawn clearance and relaunch.")); return; }
        }
        else if (Action != 2)
            for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
            {
                const bool Hit = Action == 1 ? FVector::Dist2D(It->GetActorLocation(), GS->HazardLocation) < 500
                    : FVector::Dist2D(It->GetActorLocation(), Boss->GetActorLocation()) < 700
                        && FVector::DotProduct(Boss->GetActorForwardVector(), (It->GetActorLocation()-Boss->GetActorLocation()).GetSafeNormal2D()) > .5;
                if (Hit) UWarCombatStatus::Damage(*It, Boss, Action == 1 ? 450 : 300, 3000);
            }
        ++CommanderSequence; CommanderReleaseAt = 0; CommanderActionAt = Now + 6;
        GS->CommanderAction.Reset(); GS->HazardUntil = 0;
    }
    else if (Victim && Now >= CommanderActionAt)
    {
        const int32 Action = CommanderSequence % 3;
        Boss->SetActorRotation((Victim->GetActorLocation()-Boss->GetActorLocation()).Rotation());
        GS->CommanderAction = Action == 0 ? TEXT("Frontal strike — move behind the commander") : Action == 1 ? TEXT("Ground strike — leave the marked area") : TEXT("Rally — interrupt the commander");
        GS->HazardLocation = Action == 1 ? Victim->GetActorLocation() : Boss->GetActorLocation();
        CommanderReleaseAt = Now + 3; GS->HazardUntil = Action == 2 ? 0 : CommanderReleaseAt; bCommanderInterrupted = false;
    }
}
void AWarSiegeGameMode::Tick(float Delta)
{
    Super::Tick(Delta); auto* GS = SiegeState(); if (!GS || !Battlefield) return;
    if (GS->Siege.Phase != EWarSiegePhase::Active && GS->Siege.Phase != EWarSiegePhase::Transition) return;
    if (GS->Siege.Phase == EWarSiegePhase::Active && GS->Siege.Stage != StartedStage) StageStarted();
    FWarSiegePresence P;
    if (GS->Siege.Phase == EWarSiegePhase::Active)
    {
        if (GetWorld()->GetTimeSeconds() >= GS->NextWaveAt) Wave();
        if (GS->Siege.Phase != EWarSiegePhase::Active) return;
        Encounters(Delta);
        if (GS->Siege.Phase != EWarSiegePhase::Active) return;
        for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
        {
            if (!IsParticipant(*It) || It->IsDead() || !It->IsVisualReady() || It->IsDevelopmentFlying() || IsProtected(*It)) continue;
            const bool Attacker = It->GetPlayerState<AWarPlayerState>()->GetRealm() == EWarRealm::Riftbound;
            const auto Within = [&](const FVector& Location, const AActor* Target)
            {
                if (FVector::Dist2D(It->GetActorLocation(), Location) > Battlefield->ObjectiveRadius
                    || FMath::Abs(It->GetActorLocation().Z - Location.Z) >= 250) return false;
                FHitResult Hit;
                FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeObjective), false, *It);
                // Nearby users behind a wall cannot capture through it.
                return !GetWorld()->LineTraceSingleByChannel(Hit, It->GetActorLocation(), Location + FVector(0,0,100), ECC_Visibility, Query)
                    || (Target && Hit.GetActor() == Target);
            };
            if (Within(TaskLocation(), Crew.IsValid() ? Crew->GetPawn() : nullptr)) { if (Attacker) ++P.Attackers; else ++P.Defenders; }
            if (Within(Battlefield->OptionalObjectives[GS->Siege.Stage], Battlefield->WarEffortProps[GS->Siege.Stage]))
            { if (Attacker) ++P.OptionalAttackers; else ++P.OptionalDefenders; }
        }
        P.bCrewAlive = Crew.IsValid() && Crew->GetPawn();
        if (P.bCrewAlive && !WarSiege::IsEscort(GS->Siege))
            P.bCrewAlive = FVector::Dist2D(Crew->GetPawn()->GetActorLocation(), TaskLocation()) <= Battlefield->ObjectiveRadius;
        if (GS->Siege.Stage == 0)
            for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && B->Unit == EWarSiegeUnit::Emplacement) P.OptionalAttackers = 0;
        if (WarSiege::IsEscort(GS->Siege) && P.bCrewAlive)
        {
            auto* CrewPawn = Cast<AWarSiegeCharacter>(Crew->GetPawn());
            const FVector End = Battlefield->Objective(0, GS->Siege.Objective);
            P.bEscortAtCheckpoint = FVector::Dist2D(CrewPawn->GetActorLocation(), End) < 150;
            CrewPawn->CrewMoveSpeed = 100 * WarSiege::ParticipationRate(P.Attackers, true);
            if (P.Attackers > 0 && P.Defenders == 0) Crew->MoveToLocation(End, 60);
            else Crew->StopMovement();
        }
        const auto* Boss = Commander.IsValid() ? Cast<AWarCharacter>(Commander->GetPawn()) : nullptr;
        P.bCommanderDead = Boss && Boss->IsDead();
        P.bRecentCommanderDamage = GetWorld()->GetTimeSeconds() - CommanderDamageAt < 10;
    }
    const auto Before = GS->Siege;
    WarSiege::Tick(GS->Siege, P, Delta);
    Battlefield->ApplyMilestones(GS->Siege);
    if (Before.Objective != GS->Siege.Objective || Before.Phase != GS->Siege.Phase || Before.bOptionalComplete != GS->Siege.bOptionalComplete)
        UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_PROGRESS stage=%d objective=%d phase=%d optional=%d attackers=%d defenders=%d"), GS->Siege.Stage, GS->Siege.Objective, int32(GS->Siege.Phase), GS->Siege.bOptionalComplete, P.Attackers, P.Defenders);
    if (Before.Phase != EWarSiegePhase::Finished && GS->Siege.Phase == EWarSiegePhase::Finished)
    { UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_RESULT attackersWon=%d"), GS->Siege.bAttackersWon); ClearUnits(false); }
    Publish();
}
void AWarSiegeGameMode::Publish()
{
    auto* GS = SiegeState(); const auto& S = GS->Siege;
    const TCHAR* Labels[] = {TEXT("Secure supplies"), TEXT("Escort crew to checkpoint one"), TEXT("Escort crew to checkpoint two"), TEXT("Protect the gate breach"), TEXT("Disable first gate defense"), TEXT("Disable second gate defense"), TEXT("Hold gate controls and protect engineers"), TEXT("Defeat the Bastion commander")};
    GS->Status = S.Phase == EWarSiegePhase::Finished ? (S.bAttackersWon ? TEXT("Riftbound victory") : TEXT("Aegis victory"))
        : S.Phase == EWarSiegePhase::Transition ? TEXT("Regroup for the next stage") : Labels[S.Stage == 0 ? S.Objective : S.Stage == 1 ? 4 + S.Objective : 7];
    GS->ObjectiveLocation = TaskLocation(); GS->OptionalLocation = Battlefield->OptionalObjectives[S.Stage];
    GS->RosterLabels.Reset();
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
        if (IsParticipant(*It)) GS->RosterLabels.Add(It->GetPlayerState<AWarPlayerState>()->GetPlayerName());
    GS->ForceNetUpdate();
}
