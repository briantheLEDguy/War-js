#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Dom/JsonObject.h"
#include "WarSiegeRules.h"
#include "WarCitadelSiegeProof.generated.h"

/** Exact receipt hashing through the engine crypto provider; unavailable inputs fail recoverably. */
namespace WarCitadelProofHash
{
    AEGISWAR_API bool Bytes(const uint8* Data, int64 Length, FString& OutHash, FString& Error);
    AEGISWAR_API bool Text(const FString& Value, FString& OutHash, FString& Error);
    AEGISWAR_API bool File(const FString& Filename, FString& OutHash, FString& Error);
}

/** Exact private candidate fixture. It never publishes traversal, roster or release approval. */
UCLASS()
class AEGISWAR_API UWarCitadelSiegeProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual TStatId GetStatId() const override;
    virtual void Tick(float Delta) override;
private:
    bool Load(FString& Error);
    bool Start(FString& Error);
    void Drive();
    bool SpawnLivePlayers(class AWarSiegeBattlefield* Field,FString& Error);
    void DriveLivePlayers();
    bool ExpectedFinishedOutcome(const FWarSiegeState& State) const;
    bool LiveCharacterWitnesses(TArray<TSharedPtr<FJsonValue>>& Rows,FString& Error) const;
    void Finish(bool Passed, const FString& Detail);
    bool LoadPerformance(const TSharedPtr<FJsonObject>& Config,FString& Error);
    bool CheckPerformanceBindings(FString& Error) const;
    bool CheckBaselineBindings(FString& Error) const;
    TSharedPtr<FJsonObject> PerformanceSettings() const;
    void SamplePerformance();
    bool FinishPerformance(bool GameplayPassed,FString& Error);
    bool BenchmarkGoal(int32 Slot,FVector& Goal) const;
    bool ObserveBaselineProgression(FString& Error,bool Force=false);
    TSharedPtr<FJsonObject> BaselineProgression() const;
    friend class FWarCitadelBaselineTest;
    friend class FWarCitadelRecoveryWalWitnessTest;
    friend class FWarCitadelDefendedCampaignTest;
    bool LoadRecovery(const TSharedPtr<FJsonObject>& Config,FString& Error);
    bool CheckRecoveryBindings(FString& Error) const;
    void TickRecovery();
    bool PrepareRecoveryCast(class AWarPlayerController* Player,FString& Error);
    TSharedPtr<FJsonObject> RecoveryWalCharacter(class AWarPlayerController* Player,TSharedPtr<FJsonObject>& Witness,FString& Error) const;
    TSharedPtr<FJsonObject> RecoveryWitness(class AWarPlayerController* Player) const;
    void FinishRecovery(bool Passed,const FString& Detail);
    FString ConfigPath, Map, Revision, Signature, MapHash;
    bool bLoaded = false, bFinished = false, bFixtureReview = false, bLive = false;
    bool bLiveDefended=false,bLivePreparationObserved=false,bLiveServicesSuspendedObserved=false,bLiveCustodyHeldObserved=false;
    bool bConcurrentSides = false, bLockedCenter = false, bSawContest = false;
    bool bSentinelIntact = true;
    int32 Round = 0, Actions = 0, MaxAegis = 0, MaxRiftbound = 0;
    double Began = 0, NextDrive = 0, NextSample = 0, Movement = 0;
    double MaxElapsed = 3900;
    FString PendingSettlement;
    FString LastStartupReason;
    TArray<FString> LiveIds;
    TArray<TWeakObjectPtr<class AWarPlayerController>> LivePlayers;
    TMap<FString,FString> LiveInitialInventories;
    TMap<TWeakObjectPtr<class AWarCharacter>,FVector> Waypoints;
    UPROPERTY() TObjectPtr<class AWarSiegeEncounter> Encounter;
    UPROPERTY() TObjectPtr<class AWarCharacter> Sentinel;
    TMap<TWeakObjectPtr<class AWarCharacter>, FVector> Positions;
    TArray<TSharedPtr<FJsonValue>> Rounds, Samples;
    bool bPerformance=false, bPerformanceWriteFailed=false, bPerformanceBaseline=false;
    bool bBaselineStarted=false, bBaselineSettled=false;
    FWarSiegeState BaselinePrevious;
    double BaselineTransitionAt[2]={-1,-1};
    TArray<TSharedPtr<FJsonValue>> BaselineObservations;
    int32 PerformanceStage=-1, PerformanceFrames=0;
    double PerformanceBegan=0, PerformancePrevious=0, PerformanceStageBegan=0;
    double PerformanceRunStart=-1, PerformanceRunSeconds=0;
    int32 PerformanceRunFrames=0;
    FString PerformanceConfigHash, PerformanceFramesPath;
    TSharedPtr<FJsonObject> PerformanceBindings, PerformanceHardware, PerformanceSourceCity, PerformanceBlueprint, PerformanceBaselineManifest;
    TArray<TSharedPtr<FJsonValue>> PerformanceCameras, PerformanceWindows, PerformanceRoster, PerformancePositions;
    FString PerformanceRosterHash, PerformanceRosterCanonical, PerformanceStatsMode;
    TMap<TWeakObjectPtr<class AWarSiegeBotController>,int32> PerformanceSeats;
    TUniquePtr<FArchive> PerformanceWriter;
    UPROPERTY() TObjectPtr<class ACameraActor> PerformanceCamera;
    bool bRecoveryProof=false,bRecoveryRestored=false,bRecoveryMutation=false,bRecoveryHeld=false;
    int32 RecoveryAttempt=0;
    double RecoveryNextMutation=0;
    double RecoveryNextProgress=0;
    int32 RecoveryProgressSequence=0;
    FString RecoveryFixture,RecoveryConfigHash,RecoveryHost,RecoveryWalDirectory;
    TSharedPtr<const struct FWarAbilityDefinition> RecoveryCastDefinition;
    TSharedPtr<FJsonObject> RecoveryCastWitness;
    FGuid RecoveryReceipts[2];
    TSharedPtr<FJsonObject> RecoveryConfig;
    TArray<TSharedPtr<FJsonObject>> RecoveryExpected;
    TSet<FString> RecoveryLeaveRequested;
};
