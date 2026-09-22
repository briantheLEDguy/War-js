#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarEnemyProof.generated.h"

UCLASS()
class AEGISWAR_API UWarEnemyProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual TStatId GetStatId() const override;
    virtual void Tick(float DeltaSeconds) override;
private:
    int32 Stage = 0, Hits = 0;
    double NextStep = 0, Deadline = 0, DeathAt = 0;
    bool bFinished = false, bDamagedPlayer = false;
    float HealthBefore = 0, ManaAfter = 0;
    int64 XpBefore = 0;
    FGuid DeathEvent;
    FVector Home = FVector::ZeroVector;
    void Finish(bool bPassed, const FString& Detail);
};
