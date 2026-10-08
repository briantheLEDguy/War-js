#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarT1TraversalProof.generated.h"

class AWarCharacter;
class AController;

/** Isolated development fixture: no frontend, campaign admission, default model or GM writes. */
UCLASS()
class AEGISWAR_API AWarT1TraversalGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AWarT1TraversalGameMode();
    virtual void StartPlay() override;
    virtual void PreLogin(const FString& Options, const FString& Address, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage) override;
};

/** Walks unchanged private candidates with the normal character movement component. */
UCLASS()
class AEGISWAR_API UWarT1TraversalProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    static bool ValidSelector(const FString& Selector);
    static bool ValidCandidate(const FString& Package, const FString& Zone);
private:
    bool InitializeProof(FString& Error);
    bool StartRoute(FString& Error);
    bool GroundPoint(const TSharedPtr<FJsonObject>& Point, FVector& Ground, FString& Error) const;
    void CompleteRoute();
    void Finish(bool Passed, const FString& Detail);
    TWeakObjectPtr<AWarCharacter> Pawn;
    TWeakObjectPtr<AController> Controller;
    TSharedPtr<FJsonObject> Config, Row;
    TArray<TSharedPtr<FJsonValue>> Routes, Results;
    TArray<FVector> Targets;
    TSet<int32> CapturePoints, Captured;
    FString Directory, Zone;
    FVector Previous;
    int32 Route = -1, Waypoint = 1, Frames = 0;
    double Started = -1, RouteStarted = 0, SettleUntil = 0, CaptureUntil = 0;
    double WallStarted = 0, Distance = 0, Stalled = 0, Airborne = 0, LongestAirborne = 0;
    float InputScale = 1;
    bool bInitialized = false, bFinished = false, bCapture = false, bScreenshotRequested = false;
};
