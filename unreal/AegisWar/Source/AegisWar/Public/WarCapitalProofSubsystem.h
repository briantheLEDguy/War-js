#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarCapitalProofSubsystem.generated.h"

/** Opt-in local development acceptance. Never instantiated in Shipping. */
UCLASS()
class AEGISWAR_API UWarCapitalProofSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool bPassed, const FString& Detail);
    double StartedAt = -1;
    FVector StartPosition = FVector::ZeroVector;
    FVector FlightPosition = FVector::ZeroVector;
    double FlightStartedAt = -1;
    bool bTraversalVerified = false;
    bool bPlacementSnappingVerified = false;
    bool bCatalogSearchVerified = false;
    bool bExactTransformVerified = false;
    int32 Stage = 0;
    bool bFinished = false;
};
