#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarTrainingDummyProof.generated.h"

/** Opt-in development verification against the saved capital levels. */
UCLASS()
class AEGISWAR_API UWarTrainingDummyProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual TStatId GetStatId() const override;
    virtual void Tick(float DeltaSeconds) override;
private:
    int32 Stage = 0, Capital = 0, Checked = 0;
    double Deadline = 0, NextStep = 0;
    bool bFinished = false;
    bool bStrikeChecked = false;
    float StrikeMana = 0;
    void Finish(bool bPassed, const FString& Detail);
};
