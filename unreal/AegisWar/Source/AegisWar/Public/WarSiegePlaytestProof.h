#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarSiegePlaytestProof.generated.h"
class AWarCharacter;

/** Test-only navigation hints. Clients still send normal movement and ability RPCs. */
UCLASS()
class AWarSiegeTestDriver : public AActor
{
    GENERATED_BODY()
public:
    AWarSiegeTestDriver();
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    double Travelled = 0;
    int32 ActionRequests = 0;
private:
    UPROPERTY(Replicated) FVector Waypoint = FVector::ZeroVector;
    UPROPERTY(Replicated) bool bMove = false;
    UPROPERTY(Replicated) TObjectPtr<AWarCharacter> Enemy;
    TWeakObjectPtr<AWarCharacter> PreviousPawn;
    FVector PreviousPosition = FVector::ZeroVector;
    double NextPath = 0, NextAction = 0;
};

UCLASS()
class UWarSiegePlaytestProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
private:
    TSet<TWeakObjectPtr<APlayerController>> Drivers;
    TSet<int32> Results, ActiveRounds, CombatCaptures, TargetCaptures;
    TArray<TSharedPtr<class FJsonValue>> RoundReports;
    double PhaseAt = 0, NextLobbyAction = 0, NextSnapshot = 0;
    int32 PreviousRound = -1, PreviousPhase = -1, SelectedForRound = -1;
    bool Finished = false;
    void Capture(const FString& Name);
    void Finish(bool Passed,const FString& Detail);
};
