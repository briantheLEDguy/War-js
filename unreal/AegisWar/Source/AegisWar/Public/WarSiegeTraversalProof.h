#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarSiegeTraversalProof.generated.h"
class AWarCharacter;
class AWarSiegeBattlefield;

/** Opt-in movement fixture in the isolated map; never changes content review flags. */
UCLASS()
class AEGISWAR_API UWarSiegeTraversalProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual TStatId GetStatId() const override;
    virtual void Tick(float Delta) override;
private:
    bool SpawnCrowd(FString& Error);
    bool StartRoute(FString& Error);
    void Finish(bool Passed, const FString& Detail);
    UPROPERTY() TObjectPtr<AWarSiegeBattlefield> Battlefield;
    UPROPERTY() TArray<TObjectPtr<AWarCharacter>> Walkers;
    TArray<FVector> Destinations;
    TArray<FVector> Previous;
    TArray<float> Distance;
    TArray<float> Stalled;
    TArray<bool> Jumped;
    double StartedAt = -1;
    double PhaseAt = 0;
    int32 Phase = 0;
    int32 Route = -1;
    bool Finished = false;
};
