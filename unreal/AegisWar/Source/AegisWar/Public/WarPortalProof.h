#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarPortalProof.generated.h"

/** Opt-in local development traversal evidence; never enabled in normal sessions. */
UCLASS()
class AEGISWAR_API UWarPortalProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    TWeakObjectPtr<class AWarCharacter> RespawnPawn;
    FName RespawnZone;
    int32 RespawnRevision = INDEX_NONE;
    void Finish(bool bPassed, const FString& Detail);
    int32 Step = 0;
    int32 ResourcesGathered = 0;
    bool bResourcesVerified = false;
    bool bFullInventoryVerified = false;
    TWeakObjectPtr<class AWarZonePortal> ActivePortal;
    TWeakObjectPtr<class AWarCharacter> TravelPawn;
    int32 TravelRevision = 0;
    double TravelDeadline = 0;
    double LoadDeadline = 0;
    int32 DeferredRoutes = 0;
    int32 StreamingChecks = 0;
    FName GmObjectId;
    FString GmSnapshot;
    bool GmOriginalHidden = false;
    bool bGmVerified = false;
    bool bGmUnloadedVerified = false;
    FVector OriginalPosition = FVector::ZeroVector;
    double NextStep = 0;
    bool bFinished = false;
};
