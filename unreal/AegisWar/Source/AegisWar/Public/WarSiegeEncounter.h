#pragma once
#include "CoreMinimal.h"
#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.generated.h"
class AWarPlayerState;

/** Replicated, server-owned encounter. It never owns unrelated campaign pawns. */
UCLASS()
class AEGISWAR_API AWarSiegeEncounter : public AActor
{
    GENERATED_BODY()
public:
    AWarSiegeEncounter();
    static AWarSiegeEncounter* Find(const UWorld* World);
    static AWarSiegeEncounter* Capital(const UWorld* World);
    static AWarSiegeEncounter* For(const AActor* Actor);
    static bool SharesCombatScope(const AActor* Source, const AActor* Target);
    bool IsCapitalOccupant(const AWarCharacter* Pawn) const;
    bool CanEvacuate(EWarRealm Realm, FName Zone) const;
    TMap<EWarRealm, TSet<FName>> SafeEvacuationZones;
    bool bRecoveringCharacters = false;
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    AWarSiegeEncounter* SiegeState() { return this; }
    const AWarSiegeEncounter* SiegeState() const { return this; }
    bool FindBattlefield(FString& Error);
    bool StartRound(int32 Capacity, int32 Seed, EWarSiegeScenario Scenario, FString& Error);
    void ResetRound();
    void Wave();
    bool ValidateEquipmentStaging(FString& Error);
    bool IsParticipant(const AWarCharacter* Pawn) const;
    bool Owns(const AWarPlayerState* Player) const;
    bool IsProtected(const AActor* Actor) const;
    bool HandlesDeath(AWarCharacter* Character);
    void RespawnAfterDeath(AWarCharacter* Character);
    FVector TaskLocation(int32 PreferredSide = 0) const;
    TConstArrayView<TObjectPtr<class AWarSiegeEquipment>> ConvoyVehicles() const { return Convoy; }
    void CommanderDamaged();
    bool Enroll(AWarPlayerController* Player, FString& Error, bool bRecordedRecovery = false);
    void Leave(AController* Controller);
    void Publish();
    void FailMatch(const FString& Error);
    bool BlocksCapitalEntry(const AWarPlayerState* Player) const;
    bool SuspendsServices(FName Zone) const;
    bool StageCampaignParticipants(FString& Error);
    bool FindCampaignSpawnCenter(AWarPlayerController* Player, FVector& Center, FString& Error, bool bRecordedRecovery = false) const;
    bool StageCampaignParticipant(AWarPlayerController* Player, FString& Error, bool bRecordedRecovery = false);
    void BeginCampaignPreparation(const FString& Activation, const FString& Revision, int32 CampaignRound);
    void CompleteCampaign();
    UPROPERTY(Replicated) bool bCampaign = false;
    UPROPERTY(Replicated) FString ActivationId;
    UPROPERTY(Replicated) FString ContentRevision;
    UPROPERTY(Replicated) double PreparationUntil = 0;
    UPROPERTY(Replicated) bool bPreparing = false;
    UPROPERTY(Replicated) bool bLeasePaused = false;
    UPROPERTY(Replicated) bool bContentBlocked = false;
    UPROPERTY(Replicated) bool bCheckpointPending = false;
    UPROPERTY(Replicated) TObjectPtr<AWarSiegeBattlefield> Battlefield;
    UPROPERTY(Replicated) FWarSiegeState Siege;
    UPROPERTY(Replicated) FString Status;
    UPROPERTY(Replicated) double NextWaveAt = 0;
    UPROPERTY(Replicated) FVector ObjectiveLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) FVector LeftLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) FVector RightLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) FVector OptionalLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) FVector HazardLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) double HazardUntil = 0;
    UPROPERTY(Replicated) FString CommanderAction;
    UPROPERTY(Replicated) TArray<FString> RosterLabels;
    UPROPERTY(Replicated) bool bDevelopmentLobby = false;
    UPROPERTY(Replicated) bool bQueuedScenario = false;
    UPROPERTY(Replicated) bool bContentReady = false;
    UPROPERTY(Replicated) int32 RoundId = 0;
    UPROPERTY(Replicated) TArray<int32> ReadyPlayers;
    UPROPERTY(Replicated) float CrewHealth = 0;
    UPROPERTY(Replicated) float CrewMaxHealth = 0;
    UPROPERTY(Replicated) bool bContested = false;
    UPROPERTY(Replicated) int32 Deaths = 0;
    double GetServerWorldTimeSeconds() const;
private:
    friend class UWarCitadelSiegeProof;
    friend class FWarCitadelPhysicalSnapshotTest;
    friend class FWarSiegeEscortSeatTest;
    FWarSiegePresence LastSampledPresence;
    double LastPresenceSampleAt = -1;
    void EndRound();
    void ClearRoundEffects();
    void AssignSquads();
    void StageStarted();
    void Encounters(float Delta);
    AWarSiegeBotController* SpawnUnit(EWarRealm Realm, EWarSiegeRole CombatRole, EWarSiegeUnit Unit,
        UWarCharacterVisualDefinition* Visual, const FVector& Position);
    void ClearUnits(bool bParticipants);
    TWeakObjectPtr<AWarSiegeBotController> Crew, Commander;
    UPROPERTY() TArray<TObjectPtr<class AWarSiegeEquipment>> Convoy;
    bool PrepareConvoy();
    bool ConvoyAlive() const;
    void DriveConvoy(const FWarSiegePresence& Presence, float Delta);
    TArray<TWeakObjectPtr<AWarSiegeBotController>> Units;
    TArray<TWeakObjectPtr<AController>> Members;
    double NextEvacuationAt = 0, NextStartAttemptAt = 0;
    double CrewAt = 0, ReinforcementAt = 0, CommanderDamageAt = -100, CommanderEngagedAt = 0;
    double CommanderActionAt = 0, CommanderReleaseAt = 0;
    int32 CommanderSequence = 0, StartedStage = -1;
    bool bCommanderInterrupted = false;
    FRandomStream Random;
    void EvacuateNonparticipants();
};
