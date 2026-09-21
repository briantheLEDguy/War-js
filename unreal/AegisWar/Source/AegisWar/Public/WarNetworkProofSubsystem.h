#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarNetworkProofSubsystem.generated.h"

/** Opt-in development acceptance driver; never created in Shipping or ordinary sessions. */
UCLASS()
class AEGISWAR_API UWarNetworkProofSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool bPassed, const FString& Detail);
    double StartedAt = -1;
    double PairReadyAt = -1;
    FVector InitialAttackerPosition = FVector::ZeroVector;
    int32 StrikeRequests = 0;
    bool bMoved = false;
    bool bAutonomous = false;
    bool bMovementAnimation = false;
    bool bStrikeAnimation = false;
    bool bFinished = false;
    bool bInventoryRequestsSent = false;
    bool bInventoryVerified = false;
    float ObservedHealth = -1;
    float ObservedMana = -1;
    FString ResultRole;
};
