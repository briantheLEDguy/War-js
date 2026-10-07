#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Components/SlateWrapperTypes.h"
#include "WarDutchBastionProof.generated.h"

class ACameraActor;
class AWarCharacter;
class AHUD;
class UUserWidget;
class FJsonObject;
namespace WarCitadelCapsulePolicy { struct FKinematicsBaseline; }
namespace WarCitadelLumenStudyRuntime { class FOverride; }
struct FFindFloorResult;

/** Physical proof helpers; they never alter a route definition or gameplay review. */
namespace WarCitadelRouteWidth
{
    constexpr double MaxSpacingCm=100;
    constexpr double MovementSpacingCm=10;
    constexpr double MaxFloorDeviationCm=120;
    constexpr double GroundClearanceCm=2.4;
    struct FOverlapEvidence
    {
        int32 Queries=0,RawClear=0,Separated=0,Blocked=0,Unresolved=0,RawBlockingHits=0;
        FString LastDisposition=TEXT("unused");
        TArray<TSharedPtr<FJsonValue>> Contacts;
        void Append(const FOverlapEvidence& Other);
        TSharedPtr<FJsonObject> Json() const;
    };
    struct FSurface
    {
        TArray<FVector2D> KnotsCm;
    };
    struct FPlacement
    {
        bool Floor=false, Clear=false;
        FVector Center=FVector::ZeroVector, FloorImpact=FVector::ZeroVector;
        double FloorNormalZ=0, FloorDistance=0;
        FString Reason, FloorActor, HitActor;
        TSharedPtr<FJsonObject> Diagnostic;
        FOverlapEvidence Overlaps;
    };
    struct FTransition
    {
        bool Clear=false, StepAttempted=false, StepSucceeded=false;
        int32 MovementSteps=0;
        FVector ActualCenter=FVector::ZeroVector;
        FString Reason, HitActor;
        TSharedPtr<FJsonObject> Diagnostic;
        FOverlapEvidence Overlaps;
    };
    struct FSupport
    {
        bool Verified=false;
        double Distance=0;
        FVector Impact=FVector::ZeroVector;
        TSharedPtr<FJsonObject> Diagnostic;
    };
    /** Verify genuine line support after actual swept height adjustment; reject unsupported cached/perch cases. */
    AEGISWAR_API FSupport AdjustedSupport(AWarCharacter* Pawn,const FFindFloorResult& Before,
        const FVector& BeforeCenter,const FFindFloorResult& After,const FVector& AfterCenter);
    /** Same-world collision queries for diagnosis only; never substitutes for blocking overlap admission. */
    AEGISWAR_API TSharedPtr<FJsonObject> CapsuleContactDiagnostic(AWarCharacter* Pawn,const FVector& Center);
    AEGISWAR_API int32 Intervals(const FVector& From,const FVector& To);
    /** The signed surface changes expected height only; physical movement remains authoritative. */
    AEGISWAR_API bool ReadSurface(const TSharedPtr<FJsonObject>& Object,const FString& RouteId,FSurface& Surface);
    AEGISWAR_API bool Height(const FSurface& Surface,double X,double& Z);
    AEGISWAR_API bool Sample(const FVector& From,const FVector& To,double Width,double Radius,
        int32 Index,double Lane,FVector& Seed,double& Offset,const FSurface* Surface=nullptr);
    AEGISWAR_API FPlacement Ground(AWarCharacter* Pawn,const FVector& Feet);
    AEGISWAR_API bool SpawnPadSeed(const FVector& Anchor,double Width,double Radius,int32 Index,
        int32 X,int32 Y,const FVector2D& Gradient,FVector& Seed);
    /** Uses the real movement component's swept capsule and StepUp, in <=10 cm increments. */
    AEGISWAR_API FTransition Traverse(AWarCharacter* Pawn,const FVector& From,const FVector& To,const FSurface* Surface=nullptr);
}

/** Isolated architecture review; never updates live routing or owner drafts. */
UCLASS()
class AEGISWAR_API UWarDutchBastionProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    bool MatchesCapturedKinematics(const AWarCharacter* Pawn) const;
private:
    bool bInitialized=false, bFinished=false, bPositioned=false, bCaptured=false;
    bool bGatesTested=false;
    bool bAnchorsTested=false;
    bool bCitadelConfig=false, bCityBindingChecked=false;
    bool bCitadelWidth=false, bWidthComplete=false, bWidthPassed=true, bPhysicalPassed=true;
    bool bArchitectureUiSuppressed=false;
    bool bCinematicView=false;
    bool bViewMaterialsReady=false;
    double ViewMaterialsWaitStarted=0,NextViewMaterialCheck=0;
    double Started=-1, Next=0, RouteStarted=0;
    double ViewSettleSeconds=6;
    double LastProgress=0, BestDistance=MAX_dbl;
    int32 ViewIndex=0, RouteIndex=0, Waypoint=0;
    FString Directory, Signature;
    FString CityRevision, MapSha256;
    TArray<TSharedPtr<FJsonValue>> Views, Routes, Gates, Anchors, SpawnPads;
    TArray<TSharedPtr<FJsonValue>> GateSweeps;
    TArray<TSharedPtr<FJsonValue>> GateVerticalSweeps;
    TArray<TSharedPtr<FJsonValue>> ObjectiveSamples;
    TArray<TSharedPtr<FJsonValue>> SpawnSamples;
    TArray<TSharedPtr<FJsonValue>> PhysicalFailures;
    TArray<TSharedPtr<FJsonValue>> RouteWidthSamples;
    TSharedPtr<FJsonObject> RouteWidthConfig;
    TSharedPtr<FJsonObject> CaptureLighting;
    TSharedPtr<FJsonObject> CaptureMaterialReadiness;
    FString PrivateLumenMode, CaptureNonce;
    TSharedPtr<WarCitadelLumenStudyRuntime::FOverride> LightingOverride;
    TSharedPtr<WarCitadelCapsulePolicy::FKinematicsBaseline> KinematicsBaseline;
    int32 WidthRouteIndex=0;
    TArray<TSharedPtr<FJsonValue>> RouteFailures;
    TArray<TSharedPtr<FJsonValue>> CompletedRoutes;
    TArray<TSharedPtr<FJsonValue>> ViewPerformance;
    TArray<double> Frames;
    TArray<double> DrawCalls, Primitives;
    TArray<double> ViewFrames, ViewDrawCalls;
    int32 PeakStreamingRequests=0;
    double RouteDistance=0;
    FVector PreviousFeet=FVector::ZeroVector;
    TWeakObjectPtr<ACameraActor> Camera;
    TMap<TWeakObjectPtr<AHUD>,bool> SavedHudVisibility;
    TMap<TWeakObjectPtr<UUserWidget>,ESlateVisibility> SavedWidgetVisibility;
    void HideArchitectureUi();
    void RestoreArchitectureUi();
    void Finish(bool Passed, const FString& Detail);
};
