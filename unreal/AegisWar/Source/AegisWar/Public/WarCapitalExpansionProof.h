#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarCapitalExpansionProof.generated.h"

class ACameraActor;

/** Opt-in development evidence. Never alters the saved city or the owner's GM draft. */
UCLASS()
class AEGISWAR_API UWarCapitalExpansionProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    bool bInitialized = false, bFinished = false, bPositioned = false, bCaptured = false;
    bool bBefore = false;
    bool bGmVerified = false, bGmReloadVerified = false;
    bool bOwnerDraftImported = false, bLightingFollowsEdit = false;
    int32 ViewIndex = 0, RouteIndex = 0, Waypoint = 0;
    double Started = -1, Next = 0, RouteStarted = 0;
    FString Directory;
    TArray<TSharedPtr<FJsonValue>> Views, Routes;
    TArray<double> Frames;
    TWeakObjectPtr<ACameraActor> Camera;
    void Finish(bool Passed, const FString& Detail);
};
