#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "WarFrontendPresentation.generated.h"

class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UTextureRenderTarget2D;
class UWarCharacterVisualDefinition;
struct FStreamableHandle;
struct FWarFrontendScene;

/** A visual-only snapshot; no source actor or gameplay class is instantiated. */
USTRUCT(BlueprintType)
struct FWarFrontendPlacement
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UMaterialInterface>> Materials;
    UPROPERTY(EditAnywhere) TArray<FTransform> Instances;
};

USTRUCT(BlueprintType)
struct FWarFrontendShot
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FVector Eye = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) FVector EndEye = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) FVector Target = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) float FieldOfView = 55;
};

USTRUCT(BlueprintType)
struct FWarFrontendCity
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FName ZoneId;
    UPROPERTY(EditAnywhere) FString Label;
    UPROPERTY(EditAnywhere) TArray<FWarFrontendPlacement> Placements;
    UPROPERTY(EditAnywhere) TArray<FWarFrontendShot> Shots;
    UPROPERTY(EditAnywhere) FRotator SunDirection = FRotator(-35, -45, 0);
    UPROPERTY(EditAnywhere) FLinearColor SunColor = FLinearColor(1, .88f, .7f);
    UPROPERTY(EditAnywhere) float SunIntensity = 5;
    UPROPERTY(EditAnywhere) float SkyIntensity = 1;
    UPROPERTY(EditAnywhere) FLinearColor FogColor = FLinearColor(.12f, .18f, .25f);
};

UCLASS(BlueprintType)
class AEGISWAR_API UWarFrontendPresentationDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TArray<FWarFrontendCity> Cities;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UMaterialInterface> CharacterComposite;
    UPROPERTY(EditAnywhere) float HoldSeconds = 18;
    UPROPERTY(EditAnywhere) float FadeSeconds = 3;
    bool Validate(FString& Error) const;
};

/** Clock advances only when both views are ready; reduced motion freezes its composition. */
struct AEGISWAR_API FWarFrontendCycle
{
    double Time = 0;
    int32 Shot = 0;
    void Advance(float Delta, bool bReady, bool bReduced, float Hold, float Fade);
    float Blend(float Hold, float Fade) const;
    float Progress(float Hold, float Fade) const;
};

/** Owns render-only worlds. Lifetime follows the frontend, never the campaign pawn. */
UCLASS()
class AEGISWAR_API UWarFrontendPresentation : public UObject
{
    GENERATED_BODY()
public:
    UWarFrontendPresentation();
    virtual ~UWarFrontendPresentation() override;
    void Initialize();
    void Shutdown();
    virtual void BeginDestroy() override;
    void Tick(float Delta, bool bVisible);
    void SelectCharacter(FName Race, FName Career, FName Body);
    void Retry();
    void Rotate(float Degrees);
    void ResetRotation();
    void SetReducedMotion(bool bValue);
    bool IsReducedMotion() const { return bReducedMotion; }
    float GetBlend() const;
    int32 GetActiveCity() const { return DisplayCity; }
    FString GetCityLabel() const;
    FString GetError() const { return CityError; }
    FString GetCharacterStatus() const { return CharacterStatus; }
    UTextureRenderTarget2D* GetCityTarget(int32 Index) const;
    UMaterialInstanceDynamic* GetCharacterMaterial() const { return CharacterMaterial; }
    UTextureRenderTarget2D* GetCharacterTarget() const { return CharacterTarget; }
    bool HasCharacter() const;
    uint64 GetSelectionGeneration() const { return SelectionGeneration; }
private:
    void LoadCities();
    void FinishCharacter(uint64 Generation, UWarCharacterVisualDefinition* Visual);
    UPROPERTY(Transient) TObjectPtr<UWarFrontendPresentationDefinition> Definition;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextureRenderTarget2D>> CityTargets;
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> CharacterTarget;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CharacterMaterial;
    UPROPERTY(Transient) TObjectPtr<UWarCharacterVisualDefinition> SelectedVisual;
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> RetainedCityTarget;
    FString RetainedCityLabel;
    TSharedPtr<FWarFrontendScene> Cities[2];
    TSharedPtr<FWarFrontendScene> CharacterScene;
    TSharedPtr<FStreamableHandle> DefinitionLoad;
    TSharedPtr<FStreamableHandle> CityLoad;
    TSharedPtr<FStreamableHandle> CharacterLoad;
    FWarFrontendCycle Cycle;
    FString CityError;
    FString CharacterStatus;
    FName SelectedRace, SelectedCareer, SelectedBody;
    uint64 SelectionGeneration = 0;
    bool bRunning = false;
    bool bReducedMotion = false;
    bool bDirty = true;
    float CaptureTime = 0;
    float CharacterYaw = -15;
    float DefaultCharacterYaw = -15;
    int32 DisplayCity = 0;
};
