#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarCombatNetworkProof.generated.h"
class AWarCharacter;

/** Opt-in development proof; uses the real owner RPCs and CharacterMovement prediction. */
UCLASS()
class AEGISWAR_API UWarCombatNetworkProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual TStatId GetStatId() const override;
    virtual void Tick(float Delta) override;
private:
    void Finish(bool bPassed,const FString& Detail);
    TWeakObjectPtr<AWarCharacter> Actor, Target;
    FName Ability;
    double Started=-1, ActionAt=-1, MovementAt=-1;
    FVector MovementOrigin=FVector::ZeroVector;
    int32 Phase=0;
    bool bFinished=false, bPredictedMovement=false;
};
