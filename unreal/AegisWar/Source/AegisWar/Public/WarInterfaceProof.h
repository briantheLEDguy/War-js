#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarInterfaceProof.generated.h"

/** Opt-in development smoke test; never created in shipping or ordinary gameplay. */
UCLASS()
class AEGISWAR_API UWarInterfaceProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool Passed, const FString& Detail);
    int32 Step = 0;
    double NextStep = 0;
    bool bFinished = false;
};
