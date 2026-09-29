#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarDutchBastionProof.generated.h"

class ACameraActor;

/** Isolated architecture review; never updates live routing or owner drafts. */
UCLASS()
class AEGISWAR_API UWarDutchBastionProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    bool bInitialized=false, bFinished=false, bPositioned=false, bCaptured=false;
    double Started=-1, Next=0, RouteStarted=0;
    double ViewSettleSeconds=6;
    double LastProgress=0, BestDistance=MAX_dbl;
    int32 ViewIndex=0, RouteIndex=0, Waypoint=0;
    FString Directory, Signature;
    TArray<TSharedPtr<FJsonValue>> Views, Routes;
    TArray<TSharedPtr<FJsonValue>> RouteFailures;
    TArray<TSharedPtr<FJsonValue>> ViewPerformance;
    TArray<double> Frames;
    TArray<double> DrawCalls, Primitives;
    TArray<double> ViewFrames, ViewDrawCalls;
    int32 PeakStreamingRequests=0;
    TWeakObjectPtr<ACameraActor> Camera;
    void Finish(bool Passed, const FString& Detail);
};
