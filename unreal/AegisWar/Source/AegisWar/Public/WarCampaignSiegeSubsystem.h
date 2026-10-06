#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Dom/JsonObject.h"
#include "WarSiegeRules.h"
#include "WarCampaignSiegeSubsystem.generated.h"

class AWarSiegeEncounter;
class AWarPlayerController;
class AWarPlayerState;

enum class EWarCampaignLeaseRequest : uint8 { None, Heartbeat, Reactivate };

/** Trusted development host bridge. Production Steam admission remains separately gated. */
UCLASS()
class AEGISWAR_API UWarCampaignSiegeSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
    void Enroll(AWarPlayerController* Player, bool Join);
    void Disconnect(AWarPlayerController* Player);
    void Checkpoint(AWarPlayerController* Player, bool Evacuation = false);
    bool HasEvacuationCheckpoint(const AWarPlayerController* Player) const;
    void Evacuated(AWarPlayerController* Player);
    bool JournalsMutations(const AWarPlayerState* Player) const;
    bool CommitMutation(AWarPlayerController* Player, FString& Error);
    bool PrepareCharacter(AWarPlayerController* Player);
    /** Selects collision-checked space before the recovering avatar is created. */
    bool ResolveRecoverySpawn(AWarPlayerController* Player, FTransform& Transform, bool& bRecovering, FString& Error) const;
    bool SettlementAcknowledged(const FString& Activation, bool AttackersWon) const;
    bool HasPendingCapitalEnrollment() const;
    bool IsEnrollmentPending(const AWarPlayerController* Player) const;
    bool IsCharacterReturnPending(const AWarPlayerController* Player) const;
    static TSharedPtr<FJsonObject> Snapshot(const FWarSiegeState& State, bool Preparing, double PreparationRemaining = 180);
    static bool RestoreSnapshot(const TSharedPtr<FJsonObject>& Json, FWarSiegeState& State, FString& Error);
    static EWarCampaignLeaseRequest LeaseRequestDue(bool Paused, double Now, double Until, double NextAttempt);
private:
    friend class FWarCitadelMutationTest;
    friend class FWarCampaignCombatStateTest;
    friend class FWarCampaignRecoverySpawnTest;
    static bool FlushMutationWal(const FString& Filename, const TSharedPtr<FJsonObject>& Record, FString& Error);
    FString Url, BootstrapKey, Token, HostId;
    FString ProvisionedCharacterId;
    FString SettledActivation, SettledResult;
    FString LoadingActivation, LoadingRevision;
    bool bBusy = false, bFinishedSnapshot = false;
    double NextPoll = 0, NextHeartbeat = 0, NextStatus = 0, LeaseUntil = 0, RetryAt = 0;
    double NextAdmissionAttempt = 0;
    double BootstrapLeaseUntil = 0, NextLeaseAttempt = 0;
    int32 Sequence = 0;
    bool bReconcile = false;
    bool bOwnerLeaseReady = false;
    struct FQueuedRequest
    {
        FString Path;
        TSharedPtr<FJsonObject> Value;
        TFunction<void(bool,TSharedPtr<FJsonObject>,FString)> Reply;
    };
    TArray<FQueuedRequest> Requests;
    TMap<FString,TSharedPtr<FJsonObject>> Characters;
    TSet<FString> ApprovedIds, ConnectedIds;
    struct FReturn
    {
        TWeakObjectPtr<AWarPlayerController> Player;
        FString Activation;
        bool bEvacuation = false, bSending = false;
        TSharedPtr<FJsonObject> Document;
        bool bRebinding = false, bCommitted = false;
    };
    TMap<FString,FReturn> Returns;
    struct FRecovery
    {
        TWeakObjectPtr<AWarPlayerController> Player;
        TSharedPtr<FJsonObject> Character;
        FString Activation;
        int32 Revision = 0, WalSequence = 0;
        bool bEvacuation = false;
        bool bAcknowledging = false;
        bool bRespawnPending = false, bPawnRestored = false, bSafeRelocation = false;
        bool bReturnHandoff = false;
    };
    TMap<FString,FRecovery> Recoveries;
    TSet<FString> RestoreRequested, PendingRecovery, EvacuationReady, CheckpointQueued;
    struct FCharacterAck { int32 Revision = 0, WalSequence = 0; };
    struct FLocalWal
    {
        FString Filename;
        TSharedPtr<FJsonObject> Body;
        TWeakObjectPtr<AWarPlayerController> Player;
        bool bSending = false;
    };
    TMap<FString,FCharacterAck> CharacterAcks;
    TMap<FString,FLocalWal> LocalWals;
    FString WalDirectory, WalError;
    TSet<FString> MembershipPending, IdentityHolds;
    TMap<FString,TWeakObjectPtr<AWarPlayerController>> PendingAdmissions;
    UPROPERTY() TObjectPtr<AWarSiegeEncounter> Encounter;
    void Request(const FString& Path, TSharedPtr<FJsonObject> Body,
        TFunction<void(bool,TSharedPtr<FJsonObject>,FString)> Reply);
    TSharedPtr<FJsonObject> Body(bool Activation = false) const;
    void ApplyLease(const TSharedPtr<FJsonObject>& Lease);
    TSharedPtr<FJsonObject> Capture(AWarPlayerController* Player);
    TArray<TSharedPtr<FJsonValue>> CaptureMembers();
    void Recover(AWarPlayerController* Player);
    void FinishRecoveries();
    void AcknowledgeRecovery(const FString& Id);
    void ObserveRecovery(const TSharedPtr<FJsonObject>& Data);
    void FinishReturns();
    void SendReturnCheckpoint(const FString& Id);
    void RestoreReturnHandoff(AWarPlayerController* Player);
    void FinishAdmissions();
    void ReserveDisconnectedSeat(const TSharedPtr<FJsonObject>& AcceptedMembership);
    bool StagesRecoveryAtEntry(const FString& Id, const TSharedPtr<FJsonObject>& Character) const;
    void ObserveAcks(const TSharedPtr<FJsonObject>& Data);
    void ReplayWals();
};
