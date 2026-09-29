#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarImportedPopulationProof.generated.h"

/** Development-only checks against the exact source ledger and streamed actors. */
UCLASS()
class AEGISWAR_API UWarImportedPopulationProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual TStatId GetStatId() const override;
    virtual void Tick(float DeltaSeconds) override;
private:
    struct FExpected { FName Id, Zone, Profile, Role; FString Name; };
    TArray<FExpected> Expected;
    TArray<FName> Zones;
    TMap<FName,float> AnimationSamples;
    int32 ZoneIndex=0, Checked=0;
    bool bInitialized=false, bQueued=false, bFinished=false;
    double Started=-1, SampleTime=-1;
    void Finish(bool bPassed,const FString& Detail);
};
