#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarCityPopulationProof.generated.h"
UCLASS()
class AEGISWAR_API UWarCityPopulationProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    bool bLoaded = false;
    bool bFinished = false;
    double Started = -1;
    double AnimationSampleTime = -1;
    TMap<FName, float> AnimationSamples;
    void Finish(bool Passed, const FString& Detail);
};
