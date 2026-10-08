#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarT1ReviewProof.generated.h"

/** Exercises ordinary character entry and GM recovery in an isolated local T1 walkthrough. */
UCLASS()
class AEGISWAR_API UWarT1ReviewProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool Passed, const FString& Detail);
    bool Grounded(class AWarCharacter* Pawn) const;
    FString Run;
    FVector Arrival;
    double Next = 0;
    int32 Step = 0;
    bool bFinished = false;
};
