#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarAbilityDeploymentProof.generated.h"

/** Exercises the ordinary personal GM deploy/rollback APIs in an isolated save directory. */
UCLASS()
class AEGISWAR_API UWarAbilityDeploymentProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type==EWorldType::Game; }
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
private:
    int32 Step=0;
    double Next=0;
    bool bFinished=false;
    FString FirstVersion;
    TArray<FString> Checks;
    bool Check(bool Passed,const FString& Label);
    void Finish(bool Passed,const FString& Detail);
};
