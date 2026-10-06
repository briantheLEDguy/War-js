#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeEquipment.h"
#include "WarScenarioInstance.h"
#include "Engine/GameInstance.h"
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
#include "WarSiegeNavigation.h"
#include "AbilitySystemComponent.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"

void AWarSiegeCharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{ Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(AWarSiegeCharacter, Unit); DOREPLIFETIME(AWarSiegeCharacter, Equipment); }
void AWarSiegeCharacter::Tick(float Delta)
{ Super::Tick(Delta); if (Unit == EWarSiegeUnit::Crew) GetCharacterMovement()->MaxWalkSpeed = CrewMoveSpeed; }
AWarSiegeGameMode::AWarSiegeGameMode()
{
    GameStateClass = AWarSiegeGameState::StaticClass(); HUDClass = AWarSiegeHud::StaticClass();
    PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickInterval = .05f;
}
AWarSiegeEncounter* AWarSiegeGameMode::SiegeState() const { return Encounter; }
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
    return StartRound(Capacity, Seed, EWarSiegeScenario::FullSiege, Error);
}


bool AWarSiegeGameMode::ResetSiege(AWarPlayerController* Gm, FString& Error)
{
    if (!Authorized(Gm, Error)) return false;
    if (!Encounter) { Error = TEXT("Siege encounter is unavailable."); return false; }
    Encounter->ResetRound(); return true;
}

void AWarSiegeGameMode::HandleStartingNewPlayer_Implementation(APlayerController* Player)
{
    if (GetGameInstance() && GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->IsEnabled())
    {
        FString JoinError; if (Encounter) Encounter->Enroll(Cast<AWarPlayerController>(Player), JoinError);
        if (auto* PS=Player->GetPlayerState<AWarPlayerState>()) SiegeState()->ReadyPlayers.AddUnique(PS->GetPlayerId());
        if (SiegeState()->Siege.Phase==EWarSiegePhase::Active) Wave();
        return;
    }
    if (IsDevelopmentPlaytest())
    {
        auto* PS = Player->GetPlayerState<AWarPlayerState>();
        if (!PS) return;
        int32 Aegis = 0, Riftbound = 0;
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (It->Get() != Player) if (const auto* Other = It->Get()->GetPlayerState<AWarPlayerState>())
            { Aegis += Other->GetRealm() == EWarRealm::Aegis; Riftbound += Other->GetRealm() == EWarRealm::Riftbound; }
        EWarRealm AssignedRealm=Aegis <= Riftbound ? EWarRealm::Aegis : EWarRealm::Riftbound;
        if (IsMenuScenario())
        {
            int32 Realm=0; FParse::Value(FCommandLine::Get(),TEXT("WarScenarioRealm="),Realm);
            // The owned server chooses the realm; a client URL cannot grant a role.
            AssignedRealm=Realm==int32(EWarRealm::Riftbound) ? EWarRealm::Riftbound : EWarRealm::Aegis;
        }
        // Realm is immutable after its initial trusted assignment.
        PS->SetDevelopmentRealm(AssignedRealm);
        PS->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        PS->SetPlayerName(FString::Printf(TEXT("Siege tester %d"), ++DevelopmentJoins));
        UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_JOIN realm=%d player=%d"), int32(PS->GetRealm()), PS->GetPlayerId());
        FString Error;
        if (!Battlefield) FindBattlefield(Error);
        if (Battlefield) for (const auto& Entry : Battlefield->Roster)
            if (Entry.Realm == PS->GetRealm() && Entry.CombatRole == EWarSiegeRole::Tank)
            { if (auto* Visual = Entry.Visual.LoadSynchronous()) Selections.Add(Player, Visual); break; }
        return;
    }
    // Existing frontend performs realm/character validation. Admission restrictions remain inherited.
    Super::HandleStartingNewPlayer_Implementation(Player);
}
APawn* AWarSiegeGameMode::SpawnDefaultPawnAtTransform_Implementation(AController* Player, const FTransform& Transform)
{
    auto* Bot = Cast<AWarSiegeBotController>(Player);
    auto* Visual = Bot ? Bot->Visual.Get() : SelectedVisual(Player);
    if (!Bot && !IsDevelopmentPlaytest()) return Super::SpawnDefaultPawnAtTransform_Implementation(Player, Transform);
    FString Error;
    auto* PS = Player->GetPlayerState<AWarPlayerState>();
    if (!PS || !Visual || !Visual->ValidateForSpawn(PS->GetRealm(), Error)) return nullptr;
    auto* Pawn = GetWorld()->SpawnActorDeferred<AWarSiegeCharacter>(AWarSiegeCharacter::StaticClass(), Transform,
        Player, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding);
    if (!Pawn) return nullptr;
    Pawn->Unit = Bot ? Bot->Unit : EWarSiegeUnit::Participant;
    if (!Pawn->SetVisualDefinition(Visual, Error)) { Pawn->Destroy(); return nullptr; }
    Pawn->FinishSpawning(Transform); return Pawn;
}
void AWarSiegeGameMode::RestartPlayer(AController* Player)
{
    if (!Player) return;
    const auto* GS = SiegeState();
    if (IsDevelopmentPlaytest() && (!GS || GS->Siege.Phase == EWarSiegePhase::Waiting || GS->Siege.Phase == EWarSiegePhase::Finished)) return;
    if (!Battlefield || !GS || GS->Siege.Phase == EWarSiegePhase::Waiting) { Super::RestartPlayer(Player); return; }
    // Only Wave admits humans during a siege; frontend entry cannot bypass slot limits.
    if (!Cast<AWarSiegeBotController>(Player)) return;
}














bool AWarSiegeGameMode::FindBattlefield(FString& Error)
{ const bool Found = Encounter && Encounter->FindBattlefield(Error); Battlefield = Encounter ? Encounter->Battlefield.Get() : nullptr; return Found; }
bool AWarSiegeGameMode::StartRound(int32 Capacity, int32 Seed, EWarSiegeScenario Scenario, FString& Error)
{ return Encounter && Encounter->StartRound(Capacity, Seed, Scenario, Error); }
void AWarSiegeGameMode::Wave() { if (Encounter) Encounter->Wave(); }
void AWarSiegeGameMode::ClearRoundEffects() {}
void AWarSiegeGameMode::ClearUnits(bool Participants) { if (Encounter && Participants) Encounter->ResetRound(); }
void AWarSiegeGameMode::Publish() { if (Encounter) Encounter->Publish(); }
bool AWarSiegeGameMode::ValidateEquipmentStaging(FString& Error) { return Encounter && Encounter->ValidateEquipmentStaging(Error); }
void AWarSiegeGameMode::CommanderDamaged() { if (Encounter) Encounter->CommanderDamaged(); }
bool AWarSiegeGameMode::IsParticipant(const AWarCharacter* Pawn) const { return Encounter && Encounter->IsParticipant(Pawn); }
bool AWarSiegeGameMode::IsProtected(const AActor* Actor) const { return Encounter && Encounter->IsProtected(Actor); }
FVector AWarSiegeGameMode::TaskLocation() const { return Encounter ? Encounter->TaskLocation() : FVector::ZeroVector; }
void AWarSiegeGameMode::RespawnAfterDeath(AWarCharacter* Character)
{ if (!Encounter || !Encounter->HandlesDeath(Character)) Super::RespawnAfterDeath(Character); }
void AWarSiegeGameMode::Tick(float Delta)
{
    Super::Tick(Delta);
    if (IsMenuScenario())
    { uint32 Parent = 0; FParse::Value(FCommandLine::Get(), TEXT("WarScenarioParentPid="), Parent);
      if (Parent && !FPlatformProcess::IsApplicationRunning(Parent)) FPlatformMisc::RequestExit(false); }
    if (Encounter && IsDevelopmentPlaytest() && (Encounter->Siege.Phase == EWarSiegePhase::Waiting
        || (!Encounter->bQueuedScenario && Encounter->Siege.Phase == EWarSiegePhase::Finished))) UpdateLobby();
}
