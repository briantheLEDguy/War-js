#include "WarSiegeEncounter.h"
#include "WarSiegeEquipment.h"
#include "WarScenarioInstance.h"
#include "Engine/GameInstance.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCharacterVisualDefinition.h"
#include "WarCombatStatus.h"
#include "WarWrathRelic.h"
#include "WarWarpIdol.h"
#include "WarAbilityRuntime.h"
#include "WarWorldEditSubsystem.h"
#include "WarGmRules.h"
#include "WarRuntimeSettings.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "WarSiegeHud.h"
#include "WarSiegeNavigation.h"
#include "AbilitySystemComponent.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarZonePortal.h"
#include "WarZoneAnchor.h"
#include "WarCampaignSiegeSubsystem.h"
#include "GameFramework/GameStateBase.h"


bool AWarSiegeEncounter::FindBattlefield(FString& Error)
{
    Battlefield = nullptr;
    for (TActorIterator<AWarSiegeBattlefield> It(GetWorld()); It; ++It)
    {
        if (Battlefield) { Error = TEXT("The siege map contains duplicate battlefield definitions."); Battlefield = nullptr; return false; }
        Battlefield = *It;
    }
    if (!Battlefield) { Error = TEXT("Open an authored siege map with a validated battlefield definition."); return false; }
    if (GetGameInstance()) if (auto* Instance=GetGameInstance()->GetSubsystem<UWarScenarioInstance>();Instance && !Instance->ReviewCandidate(Battlefield,Error)) return false;
    return true;
}
bool AWarSiegeEncounter::StartRound(int32 Capacity, int32 Seed, EWarSiegeScenario Scenario, FString& Error)
{
    auto* GS = SiegeState();
    if (!GS || !WarSiege::ValidCapacity(Capacity) || GS->Siege.Phase == EWarSiegePhase::Active || GS->Siege.Phase == EWarSiegePhase::Transition)
    { Error = TEXT("Choose 6, 12 or 18 slots and reset the previous siege before launching."); return false; }
    if (!FindBattlefield(Error) || !Battlefield->Validate(Error, Scenario, bCampaign))
    { if (!Battlefield) Error = TEXT("Open an authored siege map with a validated battlefield definition."); GS->Status = Error; return false; }
    if (GetGameInstance()) if (auto* Instance=GetGameInstance()->GetSubsystem<UWarScenarioInstance>();Instance && !Instance->ReviewCandidate(Battlefield,Error,true))
    { GS->Status=Error;return false; }
    int32 HumanCounts[2] = {};
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        const auto* PS = It->Get()->GetPlayerState<AWarPlayerState>();
        if (PS && PS->GetRealm() != EWarRealm::None && (!bCampaign || Owns(PS))) ++HumanCounts[PS->GetRealm() == EWarRealm::Aegis ? 0 : 1];
    }
    if (HumanCounts[0] > Capacity || HumanCounts[1] > Capacity)
    { Error = TEXT("Connected realm population exceeds the selected capacity."); return false; }
    ClearRoundEffects(); ClearUnits(true); Random.Initialize(Seed); StartedStage = -1;
    const auto* Instance = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarScenarioInstance>() : nullptr;
    const int32 Version = Instance && Instance->IsEnabled() ? Instance->RulesVersion() : Battlefield->DefinitionVersion;
    if (Instance && Instance->IsEnabled() && !Instance->ContentRevision().IsEmpty() && Instance->ContentRevision() != Battlefield->ReviewedCityRevision)
    { Error = TEXT("This saved scenario belongs to another city revision. Preserve it for recovery using its recorded content."); return false; }
    if (!WarSiege::Start(GS->Siege, Capacity, Scenario, Version)) { Error = TEXT("Unsupported siege scenario or capacity."); return false; }
    if (!bCampaign) for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PC = Cast<AWarPlayerController>(It->Get())) { FString JoinError; Enroll(PC, JoinError); }
    if (!bCampaign) ++GS->RoundId; GS->ReadyPlayers.Reset(); GS->Deaths = 0; GS->bContested = false;
    GS->NextWaveAt = GetWorld()->GetTimeSeconds();
    StageStarted();
    if (GS->Siege.Phase == EWarSiegePhase::Waiting) { Error = GS->Status; return false; }
    Wave();
    if (GS->Siege.Phase == EWarSiegePhase::Waiting) { Error = GS->Status; return false; }
    Publish();
    UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_START capacity=%d seed=%d definition=%d"), Capacity, Seed, Battlefield->DefinitionVersion);
    return true;
}
void AWarSiegeEncounter::FailMatch(const FString& Error)
{
    if (bCampaign)
    {
        bContentBlocked = bLeasePaused = true; bContentReady = false; Status = Error;
        ForceNetUpdate(); UE_LOG(LogTemp, Error, TEXT("WAR_CAMPAIGN_SIEGE_BLOCKED %s"), *Error); return;
    }
    ClearRoundEffects();
    ClearUnits(true); auto* GS = SiegeState(); GS->Siege.Phase = EWarSiegePhase::Waiting; GS->Status = Error;
    if (Battlefield) Battlefield->ApplyMilestones(GS->Siege);
    GS->HazardUntil = 0; GS->CommanderAction.Reset(); GS->RosterLabels.Reset();
    GS->ReadyPlayers.Reset(); GS->bContentReady = false;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PS = It->Get()->GetPlayerState<AWarPlayerState>(); Owns(PS)) { if (PS->IsSiegeNormalized()) PS->SetSiegeNormalized(false); PS->SetSiegeMembership(nullptr); }
    GS->ForceNetUpdate(); UE_LOG(LogTemp, Error, TEXT("WAR_SIEGE_BLOCKED %s"), *Error);
}
AWarSiegeBotController* AWarSiegeEncounter::SpawnUnit(EWarRealm Realm, EWarSiegeRole CombatRole, EWarSiegeUnit Unit,
    UWarCharacterVisualDefinition* Visual, const FVector& Position)
{
    FVector Center;
    if (!WarSiegeNavigation::SpawnCenter(GetWorld(),Position,Center)) return nullptr;
    auto* Controller = GetWorld()->SpawnActor<AWarSiegeBotController>();
    if (!Controller) return nullptr;
    auto* PS = Controller->GetPlayerState<AWarPlayerState>();
    if (!PS) { Controller->Destroy(); return nullptr; }
    Controller->CombatRole = CombatRole; Controller->Unit = Unit; Controller->Visual = Visual;
    if (bCampaign && !ActivationId.IsEmpty()) Controller->CampaignCombatSourceKey = FString::Printf(TEXT("encounter:%s:%d:%s:%d:%d:%s"),
        *ActivationId, SiegeState()->Siege.Stage, Realm==EWarRealm::Aegis ? TEXT("aegis") : TEXT("riftbound"),
        static_cast<int32>(Unit), Units.Num(), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
    PS->SetDevelopmentRealm(Realm); PS->SetCurrentZoneTrusted(TEXT("aegis_capital"));
    PS->SetPlayerName(Unit == EWarSiegeUnit::Participant ? FString::Printf(TEXT("[Bot] %s %d"), *Visual->ClassId.ToString(), Units.Num() + 1)
        : Unit == EWarSiegeUnit::Commander ? TEXT("Bastion Commander") : Unit == EWarSiegeUnit::Crew ? TEXT("Riftbound Breach Engineer") : TEXT("Bastion Garrison"));
    FString SpawnError;
    const FTransform Transform(FRotator::ZeroRotator, Center);
    auto* Pawn = GetWorld()->SpawnActorDeferred<AWarSiegeCharacter>(AWarSiegeCharacter::StaticClass(), Transform,
        Controller, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding);
    if (Pawn && Pawn->SetVisualDefinition(Visual, SpawnError))
    { Pawn->Unit = Unit; Pawn->FinishSpawning(Transform); Controller->Possess(Pawn); }
    else if (Pawn) Pawn->Destroy();
    if (!Controller->GetPawn()) { if (PS) PS->Destroy(); Controller->Destroy(); return nullptr; }
    PS->SetSiegeMembership(this, Unit); PS->SetSiegeNormalized(true);
    float Hp = 2000;
    if (Unit == EWarSiegeUnit::Commander) Hp = Battlefield->ReferenceDamagePerSecond * 4 * 180 * WarSiege::HealthScale(SiegeState()->Siege.Capacity);
    else if (Unit == EWarSiegeUnit::Crew) Hp = Battlefield->ReferenceDamagePerSecond * 2 * 20 * WarSiege::HealthScale(SiegeState()->Siege.Capacity);
    else if (Unit != EWarSiegeUnit::Participant) Hp = 1000;
    PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(), Hp);
    PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), Hp);
    Units.Add(Controller); return Controller;
}
void AWarSiegeEncounter::ClearUnits(bool Participants)
{
    for (const auto& Vehicle:Convoy) if (IsValid(Vehicle)) Vehicle->Destroy(); Convoy.Reset();
    for (auto& Weak : Units) if (auto* Bot = Weak.Get(); Bot && (Participants || Bot->Unit != EWarSiegeUnit::Participant))
    {
        if (Bot->GetPawn()) Bot->GetPawn()->Destroy();
        if (Bot->PlayerState) Bot->PlayerState->Destroy();
        Bot->Destroy();
    }
    Units.RemoveAll([](const auto& U) { return !U.IsValid(); }); Crew.Reset(); Commander.Reset();
}
void AWarSiegeEncounter::RespawnAfterDeath(AWarCharacter* Character)
{
    if (!Character || !HasAuthority()) return;
    if (!SiegeState() || SiegeState()->Siege.Phase == EWarSiegePhase::Waiting) { return; }
    if (SiegeState()->Siege.Phase == EWarSiegePhase::Finished) return;
    auto* Controller = Character->GetController();
    if (!Controller) return;
    if (bCampaign) if (auto* PC = Cast<AWarPlayerController>(Controller))
        if (auto* Bridge = GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>()) Bridge->Checkpoint(PC);
    ++SiegeState()->Deaths;
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
bool AWarSiegeEncounter::IsParticipant(const AWarCharacter* Pawn) const
{
    const auto* SiegePawn = Cast<AWarSiegeCharacter>(Pawn);
    return Pawn && (!bCampaign || IsCapitalOccupant(Pawn)) && (!SiegePawn || SiegePawn->Unit == EWarSiegeUnit::Participant)
        && Pawn->GetPlayerState<AWarPlayerState>() && Owns(Pawn->GetPlayerState<AWarPlayerState>()) && Pawn->GetPlayerState<AWarPlayerState>()->GetSiegeUnit() == EWarSiegeUnit::Participant;
}
bool AWarSiegeEncounter::IsProtected(const AActor* Actor) const
{
    const auto* GS = SiegeState();
    const auto* Pawn = Cast<AWarCharacter>(Actor);
    const auto* State = Pawn ? Pawn->GetPlayerState<AWarPlayerState>() : nullptr;
    if (bCampaign && !IsCapitalOccupant(Pawn)) return false;
    if (!Owns(State)) return bCampaign && IsCapitalOccupant(Pawn) && SuspendsServices(TEXT("aegis_capital"));
    if (bLeasePaused || bContentBlocked || bRecoveringCharacters || bCheckpointPending || !GS || GS->Siege.Phase != EWarSiegePhase::Active) return true;
    if (!Battlefield || !Actor) return true;
    for (int32 Side = 0; Side < 2; ++Side)
        if (FVector::DistSquared(Actor->GetActorLocation(), Battlefield->TeamSpawns[GS->Siege.Stage * 2 + Side]) < FMath::Square(750.f)) return true;
    return false;
}
FVector AWarSiegeEncounter::TaskLocation(int32 PreferredSide) const
{
    const auto& S = SiegeState()->Siege;
    if (S.Stage==0 && S.Objective>0 && Convoy.Num()>0 && IsValid(Convoy[0])
        && (WarSiege::IsEscort(S) || FVector::Dist2D(Convoy[0]->GetActorLocation(),Battlefield->Objective(0,3))>100))
        return Convoy[0]->GetActorLocation();
    if (WarSiege::IsEscort(S) && Crew.IsValid() && Crew->GetPawn()) return Crew->GetPawn()->GetActorLocation();
    if (Battlefield && S.Stage == 1 && S.RulesVersion >= 2 && !WarSiege::CenterUnlocked(S))
    { const int32 Side = (S.MainClaims & 0x10) ? 1 : (S.MainClaims & 0x20) ? 0 : FMath::Clamp(PreferredSide, 0, 1); return Battlefield->Objective(1, Side); }
    return Battlefield ? Battlefield->Objective(S.Stage, S.Objective) : FVector::ZeroVector;
}
void AWarSiegeEncounter::Wave()
{
    auto* GS = SiegeState(); if (!Battlefield || GS->Siege.Phase != EWarSiegePhase::Active) return;
    if (GS->Siege.Stage==0 && (!PrepareConvoy() || !ConvoyAlive())) return;
    Units.RemoveAll([](const auto& U) { return !U.IsValid(); });
    for (EWarRealm Realm : { EWarRealm::Aegis, EWarRealm::Riftbound })
    {
        TArray<APlayerController*> Humans; TArray<AWarSiegeBotController*> Bots;
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (auto* PS = It->Get()->GetPlayerState<AWarPlayerState>(); PS && Owns(PS) && PS->GetRealm() == Realm
                && (!GetGameInstance() || GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->Owns(Cast<AWarPlayerController>(It->Get())))) Humans.Add(It->Get());
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
            if (bCampaign)
            {
                auto* CurrentPawn = Cast<AWarCharacter>(PC->GetPawn());
                if (CurrentPawn && !IsCapitalOccupant(CurrentPawn)) continue;
                if (PS->GetCurrentZone() != TEXT("aegis_capital")) continue;
                if (auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>(); Streaming && !Streaming->IsZoneReady(TEXT("aegis_capital"), PC)) continue;
            }
            else PS->SetCurrentZoneTrusted(TEXT("aegis_capital"));
            const bool Respawning = !PC->GetPawn();
            if (Respawning)
            {
                FVector Center;
                if (!WarSiegeNavigation::SpawnCenter(GetWorld(),Spawn,Center))
                { UE_LOG(LogTemp,Warning,TEXT("WAR_SIEGE_SPAWN_WAIT player=%d; protected spawn is occupied"),PS->GetPlayerId()); continue; }
                GetWorld()->GetAuthGameMode<AWarGameMode>()->RestartPlayerAtTransform(PC, FTransform(FRotator::ZeroRotator,Center));
            }
            if (!PC->GetPawn()) { FailMatch(TEXT("Participant spawn failed; check the selected visual and spawn clearance.")); return; }
            if (!bCampaign && PC->GetPawn() && (Respawning || !PS->IsSiegeNormalized())) PS->SetSiegeNormalized(true);
        }
        int32 Tanks = 0, Healers = 0;
        for (int32 I = 0; I < Admitted; ++I) if (auto* Pawn = Cast<AWarCharacter>(Humans[I]->GetPawn()))
            for (const auto& E : Battlefield->Roster) if (E.Realm == Realm && E.Visual.LoadSynchronous()->ClassId == Pawn->GetCareerId())
            { Tanks += E.CombatRole == EWarSiegeRole::Tank; Healers += E.CombatRole == EWarSiegeRole::Healer; break; }
        for (auto* B : Bots) { Tanks += B->CombatRole == EWarSiegeRole::Tank; Healers += B->CombatRole == EWarSiegeRole::Healer; }
        for (int32 I = Admitted + Bots.Num(); !bCampaign && I < GS->Siege.Capacity; ++I)
        {
            const auto CombatRole = WarSiege::MissingRole(GS->Siege.Capacity, Tanks, Healers);
            TArray<const FWarSiegeRosterEntry*> Choices;
            for (const auto& E : Battlefield->Roster) if (E.Realm == Realm && E.CombatRole == CombatRole) Choices.Add(&E);
            if (Choices.IsEmpty()) { FailMatch(TEXT("The roster no longer covers a required combat role.")); return; }
            const auto* E = Choices[Random.RandRange(0, Choices.Num() - 1)];
            if (SpawnUnit(Realm, CombatRole, EWarSiegeUnit::Participant, E->Visual.LoadSynchronous(), Spawn))
            { Tanks += CombatRole == EWarSiegeRole::Tank; Healers += CombatRole == EWarSiegeRole::Healer; }
            else { FailMatch(TEXT("Bot spawn failed; check model and spawn clearance, then relaunch.")); return; }
        }
        if (GS->bQueuedScenario) UE_LOG(LogTemp,Display,TEXT("WAR_SCENARIO_TEAM realm=%d humans=%d bots=%d"),
            int32(Realm),Admitted,GS->Siege.Capacity-Admitted);
    }
    AssignSquads(); GS->NextWaveAt = GetWorld()->GetTimeSeconds() + WarSiege::WaveSeconds;
}
void AWarSiegeEncounter::AssignSquads()
{
    TMap<AController*,int32> Counts;
    TArray<AWarPlayerController*> Humans;
    for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if (auto* PC=Cast<AWarPlayerController>(It->Get()); PC && Owns(PC->GetPlayerState<AWarPlayerState>())
            && (!GetGameInstance() || GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->Owns(PC))) Humans.Add(PC);
    int32 SideCounts[2] = {};
    for (const auto& Weak:Units) if (auto* B=Weak.Get(); B && B->Unit==EWarSiegeUnit::Participant)
    {
        B->bOptionalTask=false; B->ObjectiveSide = SideCounts[B->GetPlayerState<AWarPlayerState>()->GetRealm() == EWarRealm::Aegis ? 0 : 1]++ & 1;
        auto* PC=Cast<AWarPlayerController>(B->Leader.Get());
        if (!Humans.Contains(PC) || PC->GetPlayerState<AWarPlayerState>()->GetRealm()!=B->GetPlayerState<AWarPlayerState>()->GetRealm()) B->Leader.Reset();
        else ++Counts.FindOrAdd(PC);
    }
    for (const auto& Weak:Units) if (auto* B=Weak.Get(); B && B->Unit==EWarSiegeUnit::Participant && !B->Leader.IsValid())
    {
        for (auto* PC:Humans) if (PC->GetPlayerState<AWarPlayerState>()->GetRealm()==B->GetPlayerState<AWarPlayerState>()->GetRealm()
            && (!B->Leader.IsValid() || Counts.FindRef(PC)<Counts.FindRef(B->Leader.Get()))) B->Leader=PC;
        if (B->Leader.IsValid()) ++Counts.FindOrAdd(B->Leader.Get());
    }
    // Rebalance only when a new player arrives or a permanent departure changes seats.
    for (auto* PC:Humans) for (const auto& Weak:Units)
        if (auto* B=Weak.Get(); B && B->Unit==EWarSiegeUnit::Participant && B->Leader.IsValid()
            && B->GetPlayerState<AWarPlayerState>()->GetRealm()==PC->GetPlayerState<AWarPlayerState>()->GetRealm()
            && Counts.FindRef(B->Leader.Get())>Counts.FindRef(PC)+1)
        { --Counts.FindOrAdd(B->Leader.Get()); B->Leader=PC; ++Counts.FindOrAdd(PC); }
    for (auto* PC:Humans) { PC->SiegeSquadCount=Counts.FindRef(PC); PC->ClientSiegeSquadState(PC->SiegeSquadOrder,PC->SiegeSquadCount); }
}
void AWarSiegeEncounter::StageStarted()
{
    auto* GS = SiegeState(); ClearUnits(false); StartedStage = GS->Siege.Stage;
    CrewAt = 0; CommanderDamageAt = -100; CommanderEngagedAt = GetWorld()->GetTimeSeconds();
    CommanderActionAt = CommanderEngagedAt + 6; CommanderReleaseAt = 0; CommanderSequence = 0;
    GS->HazardUntil = 0; GS->CommanderAction.Reset(); ReinforcementAt = CommanderEngagedAt;
    // Scenario stage boundaries relocate avatars. Campaign survivors retain their normal pawn/state.
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = It->Get(); if (!Owns(PC->GetPlayerState<AWarPlayerState>()) || bCampaign) continue; if (APawn* Pawn = PC->GetPawn()) { PC->UnPossess(); Pawn->Destroy(); }
    }
    for (auto& Weak : Units) if (auto* B = Weak.Get())
    { if (B->GetPawn()) B->GetPawn()->Destroy(); if (B->PlayerState) B->PlayerState->Destroy(); B->Destroy(); }
    Units.Reset(); GS->NextWaveAt = GetWorld()->GetTimeSeconds();
    if (StartedStage == 2)
    {
        Commander = SpawnUnit(EWarRealm::Aegis, EWarSiegeRole::Tank, EWarSiegeUnit::Commander, Battlefield->CommanderVisual.LoadSynchronous(), Battlefield->Objective(2,0));
        if (!Commander.IsValid()) { FailMatch(TEXT("Commander spawn failed; repair model or spawn clearance and relaunch.")); return; }
    }
    if (StartedStage == 0 && !PrepareConvoy()) return;
    if (StartedStage == 0)
        if (!SpawnUnit(EWarRealm::Aegis, EWarSiegeRole::Damage, EWarSiegeUnit::Emplacement, Battlefield->GuardVisual.LoadSynchronous(), Battlefield->OptionalObjectives[0]))
        { FailMatch(TEXT("Emplacement crew spawn failed; repair content and relaunch.")); return; }
    UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_STAGE stage=%d"), StartedStage);
}
void AWarSiegeEncounter::CommanderDamaged() { CommanderDamageAt = GetWorld()->GetTimeSeconds(); }
void AWarSiegeEncounter::Encounters(float Delta)
{
    auto* GS = SiegeState(); auto& S = GS->Siege; const double Now = GetWorld()->GetTimeSeconds();
    const bool NeedCrew = WarSiege::RequiresCrew(S);
    if (S.Stage==0 && !PrepareConvoy()) return;
    if (NeedCrew && S.Stage!=0 && !Crew.IsValid() && Now >= CrewAt)
    {
        Crew = SpawnUnit(EWarRealm::Riftbound, EWarSiegeRole::Damage, EWarSiegeUnit::Crew, Battlefield->CrewVisual.LoadSynchronous(),
            Battlefield->Objective(S.Stage, S.Stage == 0 ? S.Objective - 1 : S.Objective));
        if (!Crew.IsValid()) { FailMatch(TEXT("Breach crew spawn failed; repair content and relaunch.")); return; }
    }
    if (NeedCrew && S.Stage!=0 && !WarSiege::IsEscort(S) && Crew.IsValid()) Crew->MoveToLocation(Battlefield->Objective(S.Stage, S.Objective), 100);
    int32 LivingGuards = 0;
    for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && (B->Unit == EWarSiegeUnit::Guard || B->Unit == EWarSiegeUnit::Emplacement)) ++LivingGuards;
    const int32 WaveSize = WarSiege::Reinforcements(S.Capacity, S.bOptionalComplete && S.Stage > 0);
    if (Now >= ReinforcementAt && S.Stage < 2)
    {
        for (int32 I = 0; I < FMath::Min(WaveSize, WaveSize * 2 - LivingGuards); ++I)
            if (!SpawnUnit(EWarRealm::Aegis, EWarSiegeRole::Damage, EWarSiegeUnit::Guard, Battlefield->GuardVisual.LoadSynchronous(),
                TaskLocation(I & 1) + FVector(900 + I * 120, 900, 0)))
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
        if (auto* CombatStatus = UWarCombatStatus::On(Boss)) CombatStatus->Clear();
        for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && B->Unit == EWarSiegeUnit::Guard)
        { if (B->GetPawn()) B->GetPawn()->Destroy(); if (B->PlayerState) B->PlayerState->Destroy(); B->Destroy(); }
        GS->CommanderAction.Reset(); GS->HazardUntil = 0; CommanderReleaseAt = 0;
        CommanderDamageAt = -100; CommanderActionAt = Now + 6; CommanderEngagedAt = Now;
        UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_COMMANDER_RESET"));
    }
    if (CommanderReleaseAt > 0)
    {
        const auto* CombatStatus = UWarCombatStatus::On(Boss);
        bCommanderInterrupted |= CommanderSequence % 3 == 2 && CombatStatus && (CombatStatus->Has(TEXT("stagger")) || CombatStatus->Has(TEXT("silence")));
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
                if (Hit && IsParticipant(*It)) UWarCombatStatus::Damage(*It, Boss, Action == 1 ? 450 : 300, 3000);
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
void AWarSiegeEncounter::Tick(float Delta)
{
    Super::Tick(Delta); if (!HasAuthority()) return; auto* GS = SiegeState();
    if (bCampaign && !ActivationId.IsEmpty() && GetWorld()->GetTimeSeconds() >= NextEvacuationAt
        && (!bPreparing || GetWorld()->GetTimeSeconds() >= PreparationUntil - 60))
    { NextEvacuationAt = GetWorld()->GetTimeSeconds() + 1; EvacuateNonparticipants(); }
    if (bLeasePaused || bContentBlocked || bRecoveringCharacters || bCheckpointPending) return;
    if (bCampaign && bPreparing)
    {
        if (GetWorld()->GetTimeSeconds() < FMath::Max(PreparationUntil, NextStartAttemptAt)) return;
        FString Error;
        if (!StageCampaignParticipants(Error) || !StartRound(18, RoundId, EWarSiegeScenario::FullSiege, Error))
        { Status = Error; NextStartAttemptAt = GetWorld()->GetTimeSeconds() + 5; return; }
        bPreparing = false; bCheckpointPending = true; return;
    }
    if (!Battlefield) return;
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
            const AActor* Escort=Convoy.IsEmpty() ? static_cast<AActor*>(Crew.IsValid() ? Crew->GetPawn() : nullptr) : Convoy[0].Get();
            if (GS->Siege.Stage == 1 && GS->Siege.RulesVersion >= 2)
            {
                if (Within(Battlefield->Objective(1, 0), nullptr)) { if (Attacker) ++P.LeftAttackers; else ++P.LeftDefenders; }
                if (Within(Battlefield->Objective(1, 1), nullptr)) { if (Attacker) ++P.RightAttackers; else ++P.RightDefenders; }
            }
            if (Within(GS->Siege.Stage == 1 && GS->Siege.RulesVersion >= 2 ? Battlefield->Objective(1, 2) : TaskLocation(), Escort)) { if (Attacker) ++P.Attackers; else ++P.Defenders; }
            if (Within(Battlefield->OptionalObjectives[GS->Siege.Stage], Battlefield->WarEffortProps[GS->Siege.Stage]))
            { if (Attacker) ++P.OptionalAttackers; else ++P.OptionalDefenders; }
        }
        const auto* CrewCharacter = Crew.IsValid() ? Cast<AWarCharacter>(Crew->GetPawn()) : nullptr;
        P.bCrewAlive = GS->Siege.Stage==0 ? ConvoyAlive() : CrewCharacter && !CrewCharacter->IsDead() && CrewCharacter->IsVisualReady();
        if (P.bCrewAlive && GS->Siege.Stage!=0 && !WarSiege::IsEscort(GS->Siege))
            P.bCrewAlive = FVector::Dist2D(Crew->GetPawn()->GetActorLocation(), TaskLocation()) <= Battlefield->ObjectiveRadius;
        if (GS->Siege.Stage == 0)
            for (const auto& Weak : Units) if (auto* B = Weak.Get(); B && B->Unit == EWarSiegeUnit::Emplacement) P.OptionalAttackers = 0;
        if (GS->Siege.Stage==0 && GS->Siege.Objective>0)
        {
            DriveConvoy(P,Delta);
            P.bEscortAtCheckpoint=Convoy.Num()==2 && FVector::Dist2D(Convoy[0]->GetActorLocation(),Battlefield->EquipmentDestination(GS->Siege.Objective))<(GS->Siege.Objective==3 ? 5 : 100);
            if (!WarSiege::IsEscort(GS->Siege)) P.bCrewAlive &= P.bEscortAtCheckpoint;
        }
        else if (WarSiege::IsEscort(GS->Siege) && P.bCrewAlive)
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
    GS->bContested = (P.Attackers > 0 && P.Defenders > 0) || (P.LeftAttackers > 0 && P.LeftDefenders > 0) || (P.RightAttackers > 0 && P.RightDefenders > 0);
    const auto* CrewState = Crew.IsValid() ? Crew->GetPlayerState<AWarPlayerState>() : nullptr;
    GS->CrewHealth = CrewState ? CrewState->GetAttributes()->GetHealth() : 0;
    GS->CrewMaxHealth = CrewState ? CrewState->GetAttributes()->GetMaxHealth() : 0;
    if (GS->Siege.Stage==0)
    {
        GS->CrewHealth=GS->CrewMaxHealth=0;
        for (const auto& Vehicle:Convoy) if (IsValid(Vehicle)) for (const auto& Engineer:Vehicle->Engineers)
            if (IsValid(Engineer)) if (const auto* PS=Engineer->GetPlayerState<AWarPlayerState>())
            { GS->CrewHealth+=PS->GetAttributes()->GetHealth(); GS->CrewMaxHealth+=PS->GetAttributes()->GetMaxHealth(); }
        if (!Convoy.IsEmpty()) GS->CrewMaxHealth=Battlefield->ReferenceDamagePerSecond*40*WarSiege::HealthScale(GS->Siege.Capacity);
    }
    WarSiege::Tick(GS->Siege, P, Delta);
    if (bCampaign && (Before.Phase != GS->Siege.Phase || Before.Stage != GS->Siege.Stage || Before.MainClaims != GS->Siege.MainClaims || Before.OptionalClaims != GS->Siege.OptionalClaims)) bCheckpointPending = true;
    Battlefield->ApplyMilestones(GS->Siege);
    if (Before.Objective != GS->Siege.Objective || Before.Phase != GS->Siege.Phase || Before.bOptionalComplete != GS->Siege.bOptionalComplete)
        UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_PROGRESS stage=%d objective=%d phase=%d optional=%d attackers=%d defenders=%d"), GS->Siege.Stage, GS->Siege.Objective, int32(GS->Siege.Phase), GS->Siege.bOptionalComplete, P.Attackers, P.Defenders);
    if (Before.Phase != EWarSiegePhase::Finished && GS->Siege.Phase == EWarSiegePhase::Finished)
    { UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_RESULT round=%d attackersWon=%d elapsed=%.1f contested=%.1f deaths=%d"), GS->RoundId, GS->Siege.bAttackersWon, GS->Siege.Elapsed, GS->Siege.ContestedSeconds, GS->Deaths); EndRound(); }
    Publish();
}
void AWarSiegeEncounter::Publish()
{
    auto* GS = SiegeState(); const auto& S = GS->Siege;
    const TCHAR* Labels[] = {TEXT("Secure supplies"), TEXT("Escort siege convoy to checkpoint one"), TEXT("Escort siege convoy to checkpoint two"), TEXT("Protect the battering ram at the gate"), TEXT("Capture both courtyard side objectives"), TEXT("Capture the remaining side objective"), TEXT("Capture central plaza"), TEXT("Defeat the Bastion commander")};
    GS->Status = S.Phase == EWarSiegePhase::Finished ? (S.bAttackersWon ? TEXT("Riftbound victory") : TEXT("Aegis victory"))
        : S.Phase == EWarSiegePhase::Transition ? TEXT("Regroup for the next stage") : Labels[S.Stage == 0 ? S.Objective : S.Stage == 1 ? 4 + S.Objective : 7];
    GS->ObjectiveLocation = S.Stage == 1 && S.RulesVersion >= 2 ? Battlefield->Objective(1, 2) : TaskLocation(); GS->LeftLocation = Battlefield->Objective(1,0); GS->RightLocation = Battlefield->Objective(1,1); GS->OptionalLocation = Battlefield->OptionalObjectives[S.Stage];
    if (S.Phase==EWarSiegePhase::Active && S.Stage==0 && S.Objective>0 && !ConvoyAlive() && CrewAt>GetWorld()->GetTimeSeconds())
        GS->Status=FString::Printf(TEXT("Convoy stopped — engineers return in %.0fs"),CrewAt-GetWorld()->GetTimeSeconds());
    GS->RosterLabels.Reset();
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
        if (IsParticipant(*It)) GS->RosterLabels.Add(It->GetPlayerState<AWarPlayerState>()->GetPlayerName());
    if (auto* Legacy = GetWorld()->GetGameState<AWarSiegeGameState>())
    {
        Legacy->Siege = Siege; Legacy->Status = Status; Legacy->NextWaveAt = NextWaveAt;
        Legacy->ObjectiveLocation = ObjectiveLocation; Legacy->OptionalLocation = OptionalLocation;
        Legacy->HazardLocation = HazardLocation; Legacy->HazardUntil = HazardUntil; Legacy->CommanderAction = CommanderAction;
        Legacy->RosterLabels = RosterLabels; Legacy->bDevelopmentLobby = bDevelopmentLobby;
        Legacy->bQueuedScenario = bQueuedScenario; Legacy->bContentReady = bContentReady; Legacy->RoundId = RoundId;
        Legacy->ReadyPlayers = ReadyPlayers; Legacy->CrewHealth = CrewHealth; Legacy->CrewMaxHealth = CrewMaxHealth;
        Legacy->bContested = bContested; Legacy->Deaths = Deaths; Legacy->ForceNetUpdate();
    }
    GS->ForceNetUpdate();
}
void AWarSiegeEncounter::ClearRoundEffects()
{
    // Only enrolled characters and spawned encounter units own these effects.
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
    {
        if (!Owns(It->GetPlayerState<AWarPlayerState>())) continue;
        if (bCampaign && It->GetPlayerState<AWarPlayerState>()->GetSiegeUnit() == EWarSiegeUnit::Participant) continue;
        AWarWrathRelic::RemoveFor(*It); AWarWarpIdol::RemoveFor(*It);
        if (auto* CombatStatus = UWarCombatStatus::On(*It)) CombatStatus->Clear();
        if (auto* PS = It->GetPlayerState<AWarPlayerState>())
        {
            PS->GetClassAbilities()->Interrupt(); PS->GetClassAbilities()->ResetCooldowns(); PS->GetClassAbilities()->RestoreResource();
            PS->GetAbilitySystemComponent()->RemoveActiveEffects(FGameplayEffectQuery());
        }
    }
    // Dead humans have no pawn, but their PlayerState retains cooldowns.
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PS = It->Get()->GetPlayerState<AWarPlayerState>(); Owns(PS) && !bCampaign)
        { PS->GetClassAbilities()->Interrupt(); PS->GetClassAbilities()->ResetCooldowns(); PS->GetClassAbilities()->RestoreResource(); }
}

void AWarSiegeEncounter::EndRound()
{
    if (bCampaign) return; // Durable campaign settlement releases membership and services.
    if (GetGameInstance()) GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->Finish();
    ClearRoundEffects(); ClearUnits(true);
    auto* GS = SiegeState(); GS->ReadyPlayers.Reset(); GS->HazardUntil = 0; GS->CommanderAction.Reset();
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PS = It->Get()->GetPlayerState<AWarPlayerState>(); Owns(PS)) { if (PS->IsSiegeNormalized()) PS->SetSiegeNormalized(false); PS->SetSiegeMembership(nullptr); }

}

AWarSiegeEncounter::AWarSiegeEncounter()
{ bReplicates = true; bAlwaysRelevant = true; PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickInterval = .05f; }
AWarSiegeEncounter* AWarSiegeEncounter::Find(const UWorld* World)
{ if (World) for (TActorIterator<AWarSiegeEncounter> It(World); It; ++It) return *It; return nullptr; }
AWarSiegeEncounter* AWarSiegeEncounter::Capital(const UWorld* World)
{ if (World) for (TActorIterator<AWarSiegeEncounter> It(World); It; ++It) if (It->bCampaign && !It->ActivationId.IsEmpty()) return *It; return nullptr; }
double AWarSiegeEncounter::GetServerWorldTimeSeconds() const
{ const auto* GS = GetWorld()->GetGameState(); return GS ? GS->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds(); }
void AWarSiegeEncounter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarSiegeEncounter, Battlefield); DOREPLIFETIME(AWarSiegeEncounter, Siege);
    DOREPLIFETIME(AWarSiegeEncounter, Status); DOREPLIFETIME(AWarSiegeEncounter, NextWaveAt);
    DOREPLIFETIME(AWarSiegeEncounter, ObjectiveLocation); DOREPLIFETIME(AWarSiegeEncounter, LeftLocation); DOREPLIFETIME(AWarSiegeEncounter, RightLocation);
    DOREPLIFETIME(AWarSiegeEncounter, OptionalLocation); DOREPLIFETIME(AWarSiegeEncounter, HazardLocation);
    DOREPLIFETIME(AWarSiegeEncounter, HazardUntil); DOREPLIFETIME(AWarSiegeEncounter, CommanderAction);
    DOREPLIFETIME(AWarSiegeEncounter, RosterLabels); DOREPLIFETIME(AWarSiegeEncounter, bDevelopmentLobby);
    DOREPLIFETIME(AWarSiegeEncounter, bQueuedScenario); DOREPLIFETIME(AWarSiegeEncounter, bContentReady);
    DOREPLIFETIME(AWarSiegeEncounter, RoundId); DOREPLIFETIME(AWarSiegeEncounter, ReadyPlayers);
    DOREPLIFETIME(AWarSiegeEncounter, CrewHealth); DOREPLIFETIME(AWarSiegeEncounter, CrewMaxHealth);
    DOREPLIFETIME(AWarSiegeEncounter, bContested); DOREPLIFETIME(AWarSiegeEncounter, Deaths);
    DOREPLIFETIME(AWarSiegeEncounter, ActivationId); DOREPLIFETIME(AWarSiegeEncounter, ContentRevision); DOREPLIFETIME(AWarSiegeEncounter, bCampaign); DOREPLIFETIME(AWarSiegeEncounter, bPreparing); DOREPLIFETIME(AWarSiegeEncounter, PreparationUntil); DOREPLIFETIME(AWarSiegeEncounter, bLeasePaused); DOREPLIFETIME(AWarSiegeEncounter, bContentBlocked); DOREPLIFETIME(AWarSiegeEncounter, bCheckpointPending);
}
bool AWarSiegeEncounter::Owns(const AWarPlayerState* Player) const
{ return Player && Player->GetSiegeEncounter() == this; }
bool AWarSiegeEncounter::Enroll(AWarPlayerController* Player, FString& Error, bool bRecordedRecovery)
{
    auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!HasAuthority() || !PS || PS->GetRealm() == EWarRealm::None || Player->GetWorld() != GetWorld()
        || (PS->IsSiegeMember() && !Owns(PS)) || (bCampaign && (!bPreparing && Siege.Phase != EWarSiegePhase::Active
            && Siege.Phase != EWarSiegePhase::Transition && !(bRecordedRecovery && Siege.Phase == EWarSiegePhase::Finished))))
    { Error = TEXT("Siege enrollment is unavailable."); return false; }
    if (Owns(PS)) return true;
    int32 Count = 0;
    for (const auto& Member : Members) if (const auto* C = Member.Get())
        if (const auto* Other = C->GetPlayerState<AWarPlayerState>(); Owns(Other) && Other->GetRealm() == PS->GetRealm()) ++Count;
    if (Count >= (bCampaign ? 18 : Siege.Capacity)) { Error = TEXT("Your realm has filled its siege seats."); return false; }
    Members.AddUnique(Player); PS->SetSiegeMembership(this);
    return true;
}
void AWarSiegeEncounter::Leave(AController* Controller)
{
    auto* PS = Controller ? Controller->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!Owns(PS)) return;
    if (!bCampaign) if (auto* Pawn = Cast<AWarCharacter>(Controller->GetPawn()))
    { AWarWrathRelic::RemoveFor(Pawn); AWarWarpIdol::RemoveFor(Pawn); }
    if (PS->IsSiegeNormalized()) PS->SetSiegeNormalized(false);
    PS->SetSiegeMembership(nullptr); Members.Remove(Controller);
    if (bCampaign && !Controller->GetPawn()) if (auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>()) Mode->RestartPlayer(Controller);
}
bool AWarSiegeEncounter::HandlesDeath(AWarCharacter* Character)
{
    if (!Character || !Owns(Character->GetPlayerState<AWarPlayerState>()) || (bCampaign && !IsCapitalOccupant(Character)) || Siege.Phase == EWarSiegePhase::Waiting || Siege.Phase == EWarSiegePhase::Finished) return false;
    RespawnAfterDeath(Character); return true;
}
void AWarSiegeEncounter::ResetRound()
{
    bContentBlocked = false;
    ClearRoundEffects(); ClearUnits(true);
    const auto PreviousMembers = Members;
    for (const auto& Member : PreviousMembers) if (Member.IsValid()) Leave(Member.Get());
    for (TActorIterator<AWarPlayerState> It(GetWorld()); It; ++It) if (Owns(*It)) It->SetSiegeMembership(nullptr);
    Members.Reset(); StartedStage = -1; Siege = {}; Status = TEXT("Siege reset; awaiting launch.");
    HazardUntil = 0; CommanderAction.Reset(); RosterLabels.Reset(); ReadyPlayers.Reset();
    if (Battlefield) Battlefield->ApplyMilestones(Siege);
    ForceNetUpdate();
}
void AWarSiegeEncounter::EndPlay(const EEndPlayReason::Type Reason)
{ if (HasAuthority()) { if (auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>()) Streaming->ReleaseZone(this); ResetRound(); } Super::EndPlay(Reason); }
bool AWarSiegeEncounter::SuspendsServices(FName Zone) const
{ return bCampaign && Zone == TEXT("aegis_capital") && !ActivationId.IsEmpty(); }
bool AWarSiegeEncounter::BlocksCapitalEntry(const AWarPlayerState* Player) const
{ return SuspendsServices(TEXT("aegis_capital")) && !Owns(Player); }
void AWarSiegeEncounter::BeginCampaignPreparation(const FString& Activation, const FString& Revision, int32 CampaignRound)
{
    bContentBlocked = false;
    bCampaign = true; ActivationId = Activation; ContentRevision = Revision; RoundId = CampaignRound;
    Siege.Capacity = 18; bPreparing = true; PreparationUntil = GetWorld()->GetTimeSeconds() + 180;
    Status = TEXT("City siege preparing: enroll to participate. City services are suspended.");
    if (auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>())
    { FString Error; Streaming->EnsureZone(TEXT("aegis_capital"), Error); Streaming->PinZone(this, TEXT("aegis_capital")); }
    ForceNetUpdate();
}
void AWarSiegeEncounter::CompleteCampaign()
{ ActivationId.Reset(); bPreparing = false; if (auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>()) Streaming->ReleaseZone(this); ResetRound(); }
void AWarSiegeEncounter::EvacuateNonparticipants()
{
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* Player = Cast<AWarPlayerController>(It->Get());
        auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        auto* Pawn = Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
        if (!PS || PS->GetCurrentZone() != TEXT("aegis_capital") || Owns(PS) || !Pawn) continue;
        auto* Bridge = GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>();
        if (Bridge && (Bridge->IsEnrollmentPending(Player) || Bridge->IsCharacterReturnPending(Player))) continue;
        if (!Bridge || !Bridge->HasEvacuationCheckpoint(Player))
        { if (Bridge) Bridge->Checkpoint(Player, true); Player->ClientZoneTravelStatus(TEXT("Preserving your character before evacuation. You remain protected.")); continue; }
        FString Error = TEXT("Siege evacuation is waiting for a safe destination. You remain protected.");
        for (TActorIterator<AWarZonePortal> Portal(GetWorld()); Portal; ++Portal)
        {
            const auto* Source = AWarZoneAnchor::FindAt(GetWorld(), Portal->GetActorLocation());
            const auto* Destination = AWarZoneAnchor::FindAt(GetWorld(), Portal->ArrivalLocation);
            if (!Source || Source->ZoneId != TEXT("aegis_capital") || !Destination || !CanEvacuate(PS->GetRealm(), Destination->ZoneId)) continue;
            if (Portal->TryTraverse(Pawn, Error, true)) break;
        }
        Player->ClientZoneTravelStatus(Error);
    }
}

AWarSiegeEncounter* AWarSiegeEncounter::For(const AActor* Actor)
{
    if (!Actor) return nullptr;
    const auto* Character = Cast<AWarCharacter>(Actor);
    const auto* Controller = Cast<AController>(Actor);
    const auto* PS = Cast<AWarPlayerState>(Actor);
    if (!PS) PS = Character ? Character->GetPlayerState<AWarPlayerState>() : Controller ? Controller->GetPlayerState<AWarPlayerState>() : nullptr;
    if (PS && PS->GetSiegeEncounter()) return PS->GetSiegeEncounter();
    if (const auto* Owner = Cast<AWarSiegeEncounter>(Actor->GetOwner())) return const_cast<AWarSiegeEncounter*>(Owner);
    for (TActorIterator<AWarSiegeEncounter> It(Actor->GetWorld()); It; ++It)
        if (It->bCampaign && Character && It->IsCapitalOccupant(Character)) return *It;
    return nullptr;
}
bool AWarSiegeEncounter::IsCapitalOccupant(const AWarCharacter* Pawn) const
{
    const auto* PS = Pawn ? Pawn->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!PS || PS->GetCurrentZone() != TEXT("aegis_capital")) return false;
    const auto* Anchor = AWarZoneAnchor::FindAt(GetWorld(), Pawn->GetActorLocation());
    return Anchor && Anchor->ZoneId == TEXT("aegis_capital");
}
bool AWarSiegeEncounter::CanEvacuate(EWarRealm Realm, FName Zone) const
{ const auto* Zones = SafeEvacuationZones.Find(Realm); return Zones && Zones->Contains(Zone); }

bool AWarSiegeEncounter::SharesCombatScope(const AActor* Source, const AActor* Target)
{
    const auto ActiveEncounter = [](const AActor* Actor) {
        auto* Encounter = For(Actor);
        const auto* Pawn = Cast<AWarCharacter>(Actor);
        if (const auto* State = Cast<AWarPlayerState>(Actor)) Pawn = Cast<AWarCharacter>(State->GetPawn());
        if (const auto* Controller = Cast<AController>(Actor)) Pawn = Cast<AWarCharacter>(Controller->GetPawn());
        // A remote pending seat retains its ordinary zone combat until physical admission.
        if (Encounter && Encounter->bCampaign && !Encounter->IsCapitalOccupant(Pawn)) return static_cast<AWarSiegeEncounter*>(nullptr);
        return Encounter;
    };
    return ActiveEncounter(Source) == ActiveEncounter(Target);
}

bool AWarSiegeEncounter::StageCampaignParticipants(FString& Error)
{
    if (auto* Bridge = GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>(); Bridge && Bridge->HasPendingCapitalEnrollment())
    { Error = TEXT("Siege launch is waiting for capital enrollment acknowledgments."); return false; }
    if (!bCampaign || !Battlefield || Battlefield->TeamSpawns.Num() < 2) { Error = TEXT("Campaign staging is unavailable."); return false; }
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    TArray<TPair<AWarCharacter*,FVector>> Moved;
    const auto Hold = [&](const FString& Reason) {
        for (const auto& Row : Moved) Row.Key->TeleportTo(Row.Value, Row.Key->GetActorRotation());
        Error = Reason; return false;
    };
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = It->Get(); const auto* PS = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
        if (!Owns(PS) || PS->GetCurrentZone() != TEXT("aegis_capital")) continue;
        auto* Pawn = Cast<AWarCharacter>(PC->GetPawn());
        if (!Pawn || Pawn->IsDead() || !Pawn->IsVisualReady() || !IsCapitalOccupant(Pawn) || PS->IsScenarioTransferPending()
            || !Streaming || !Streaming->IsZoneReady(TEXT("aegis_capital"), PC))
            return Hold(TEXT("Siege launch is waiting for enrolled capital characters to finish safe admission."));
        FVector Center; const FVector Anchor = Battlefield->TeamSpawns[PS->GetRealm() == EWarRealm::Aegis ? 0 : 1];
        if (!WarSiegeNavigation::SpawnCenter(GetWorld(), Anchor, Center, Pawn))
            return Hold(TEXT("Siege launch is waiting for clear lower-city staging space."));
        const FVector Previous = Pawn->GetActorLocation();
        if (!Pawn->TeleportTo(Center, Pawn->GetActorRotation())) return Hold(TEXT("Siege staging is obstructed. Your character remains protected."));
        Moved.Emplace(Pawn, Previous); Pawn->GetCharacterMovement()->StopMovementImmediately(); Pawn->ForceNetUpdate();
    }
    return true;
}

bool AWarSiegeEncounter::FindCampaignSpawnCenter(AWarPlayerController* Player, FVector& Center, FString& Error, bool bRecordedRecovery) const
{
    auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    auto* Pawn = Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    const int32 Stage = bPreparing ? 0 : Siege.Stage;
    if (!bCampaign || !Owns(PS) || PS->GetCurrentZone()!=TEXT("aegis_capital") || !Battlefield || Stage < 0 || Stage > 2 || Battlefield->TeamSpawns.Num() != 6
        || (!bPreparing && Siege.Phase != EWarSiegePhase::Active && Siege.Phase != EWarSiegePhase::Transition
            && !(bRecordedRecovery && Siege.Phase == EWarSiegePhase::Finished)))
    { Error = TEXT("Campaign entry staging is unavailable. Your character remains protected."); return false; }
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!Streaming || !Streaming->IsZoneReady(TEXT("aegis_capital"), Player))
    { Error = TEXT("Campaign entry is waiting for your capital scene and character to be ready."); return false; }
    const FVector Anchor = Battlefield->TeamSpawns[Stage * 2 + (PS->GetRealm() == EWarRealm::Aegis ? 0 : 1)];
    if (!WarSiegeNavigation::SpawnCenter(GetWorld(), Anchor, Center, Pawn))
    { Error = TEXT("Campaign entry is waiting for clear staging space. Your character remains protected."); return false; }
    return true;
}

bool AWarSiegeEncounter::StageCampaignParticipant(AWarPlayerController* Player, FString& Error, bool bRecordedRecovery)
{
    auto* Pawn = Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    if (!Pawn || Pawn->IsDead() || !Pawn->IsVisualReady() || !IsCapitalOccupant(Pawn))
    { Error = TEXT("Campaign entry is waiting for your capital scene and character to be ready."); return false; }
    FVector Center;
    if (!FindCampaignSpawnCenter(Player,Center,Error,bRecordedRecovery)) return false;
    if (!Pawn->TeleportTo(Center,Pawn->GetActorRotation()))
    { Error = TEXT("Campaign entry staging is obstructed. Your character remains protected."); return false; }
    Pawn->GetCharacterMovement()->StopMovementImmediately(); Pawn->ForceNetUpdate(); return true;
}
