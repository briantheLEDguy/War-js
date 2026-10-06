#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarCombatUiLiveProof.generated.h"

class AWarCharacter;
class ACameraActor;
class FJsonValue;

/** Opt-in loopback proof with three real clients; never created in shipping. */
UCLASS()
class AEGISWAR_API UWarCombatUiLiveProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual TStatId GetStatId() const override;
    virtual void Tick(float Delta) override;
private:
    void Finish(bool Passed, const FString& Detail);
    FString Directory() const;
    TArray<TWeakObjectPtr<AWarCharacter>> Actors;
    TWeakObjectPtr<ACameraActor> Camera;
    TArray<TSharedPtr<FJsonValue>> Captures;
    TMap<FString, FVector> FirstPositions;
    double Started = -1, ReadyAt = -1, NextFeedback = 0;
    int32 CaptureIndex = 0;
    uint8 Observed = 0, Moved = 0;
    bool Finished = false;
};
