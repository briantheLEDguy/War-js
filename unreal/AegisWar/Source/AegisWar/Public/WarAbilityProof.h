#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarAbilityProof.generated.h"

/** Opt-in real-world combat regression, unavailable in Shipping. */
UCLASS()
class AEGISWAR_API UWarAbilityProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual TStatId GetStatId() const override;
    virtual void Tick(float DeltaSeconds) override;
private:
    void Finish(bool bPassed, const FString& Detail);
    int32 Stage = 0, Index = 0, Checked = 0;
    float TargetHealth = 0, PlayerHealth = 0, ResourceBefore = 0;
    double Next = 0, ImpactNotBefore = 0;
    FName ActiveAbility;
    TWeakObjectPtr<class AWarEnemy> TestTarget;
    bool bFinished = false;
};
