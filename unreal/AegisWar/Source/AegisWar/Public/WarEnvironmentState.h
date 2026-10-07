#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarEnvironmentState.generated.h"

USTRUCT()
struct FWarRegionalWeather
{
    GENERATED_BODY()
    UPROPERTY() FName Zone;
    UPROPERTY() FName Kind;
    UPROPERTY() float FromStrength = 0;
    UPROPERTY() float Strength = 0;
    UPROPERTY() double TransitionUnixSeconds = 0;
};

/** One authority clock survives streamed-zone changes; clients never submit environment changes. */
UCLASS()
class AEGISWAR_API AWarEnvironmentState : public AActor
{
    GENERATED_BODY()
public:
    AWarEnvironmentState();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) double AnchorUnixSeconds = 0;
    UPROPERTY(Replicated) double AnchorServerSeconds = 0;
    UPROPERTY(Replicated) TArray<FWarRegionalWeather> Regions;
    double UnixSeconds() const;
    float WeatherStrength(FName Zone) const;
    static AWarEnvironmentState* Find(UWorld* World);
    static bool IsDynamicZone(FName Zone);
    static double CycleSeconds(double UnixSeconds);
    static float Daylight(double UnixSeconds);
    static float WeatherAt(FName Zone, int64 Interval);
private:
    int64 LastWeatherInterval = MIN_int64;
};

UCLASS()
class AEGISWAR_API UWarEnvironmentSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void OnWorldBeginPlay(UWorld& World) override;
};
