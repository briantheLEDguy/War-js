#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarZoneLightingSubsystem.generated.h"

struct AEGISWAR_API FWarZoneLightingProfile
{
    FName Zone;
    FString Theme;
    FRotator SunRotation;
    FLinearColor SunColor, FillColor, FogColor;
    float SunLux, FillLux, FogDensity, FogStartCm, ExposureBias, Saturation, ShadowGamma;
    bool bAuthoredCapital = false;
};

/** Local-view environment only. No replicated lights, gameplay authority, or saved-map changes. */
UCLASS()
class AEGISWAR_API UWarZoneLightingSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
    static const TArray<FWarZoneLightingProfile>& Profiles();
    static const FWarZoneLightingProfile* FindProfile(FName Zone);
    UFUNCTION(BlueprintPure, Category="World") FName GetActiveZone() const { return ActiveZone; }
    UFUNCTION(BlueprintCallable, Category="World") bool PreviewZone(FName Zone, FVector Origin);
    UFUNCTION(BlueprintCallable, Category="World") static bool PreviewWorld(UWorld* World, FName Zone, FVector Origin);
    UFUNCTION(BlueprintPure, Category="World") static FString DescribeProfiles();
private:
    bool Apply(FName Zone, FVector Origin);
    bool CreateEnvironment();
    void HideAuthoredEnvironment();
    void RestoreAuthoredEnvironment();
    void LevelChanged(class ULevel* Level, UWorld* World);
    FDelegateHandle AddedHandle, RemovedHandle;
    bool bEnvironmentDirty = true;
    TMap<TWeakObjectPtr<class USceneComponent>, bool> AuthoredVisibility;
    UPROPERTY(Transient) TObjectPtr<class ADirectionalLight> Sun;
    UPROPERTY(Transient) TObjectPtr<class ADirectionalLight> Fill;
    UPROPERTY(Transient) TObjectPtr<class AExponentialHeightFog> Fog;
    UPROPERTY(Transient) TObjectPtr<class ASkyAtmosphere> Sky;
    UPROPERTY(Transient) TObjectPtr<class ASkyLight> Ambient;
    UPROPERTY(Transient) TObjectPtr<AActor> GradeActor;
    UPROPERTY(Transient) TObjectPtr<class UPostProcessComponent> Grade;
    FName ActiveZone;
    double NextUpdateAt = 0;
};
