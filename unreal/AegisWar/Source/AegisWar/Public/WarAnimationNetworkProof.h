#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarAnimationNetworkProof.generated.h"

class AWarCharacter;

/** Loopback-only development driver for replicated presentation and late joins. */
UCLASS()
class AEGISWAR_API UWarAnimationNetworkProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual TStatId GetStatId() const override;
    virtual void Tick(float Delta) override;
private:
    void Finish(bool bPassed,const FString& Detail);
    TArray<TWeakObjectPtr<AWarCharacter>> Actors,Targets;
    TArray<int32> Indices;
    TArray<double> Next;
    TArray<TSharedPtr<class FJsonValue>> Samples;
    TSet<FString> Seen;
    TSet<FName> InitialProfiles;
    double Started=-1;
    bool bFinished=false, bJoinedDuringAction=false, bServerReported=false;
};
