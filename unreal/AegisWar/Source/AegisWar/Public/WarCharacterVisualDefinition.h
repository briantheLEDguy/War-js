#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "WarTypes.h"
#include "WarCharacterVisualDefinition.generated.h"

class USkeletalMesh;
class UAnimInstance;
class UAnimSequence;
class UStaticMesh;

USTRUCT(BlueprintType)
struct FWarAbilityPresentation
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FName> VariantRoles;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FName> SuppliedSources;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Duration = 1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ContactSeconds = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float BlendSeconds = .14f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bStowEquipment = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Movement = TEXT("stationary");
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<float> CapsuleHeights;
};

/** Import evidence and identity travel with the asset; a mesh path alone is not an approval. */
UCLASS(BlueprintType)
class AEGISWAR_API UWarCharacterVisualDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Identity") FName ProfileKey;
    /** NPCs may explicitly reuse a source; playable visuals must use their own ProfileKey. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Provenance") FName SourceProfileKey;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Identity") FName RaceId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Identity") FName ClassId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Identity") FName BodyVariant;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Identity") EWarRealm Realm = EWarRealm::None;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Provenance") FString SourceModel;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Provenance") FString SourceSha256;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Provenance") bool bComplexAuthoredModel = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TSoftObjectPtr<USkeletalMesh> SkeletalMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TSoftClassPtr<UAnimInstance> AnimationBlueprint;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TSoftObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TMap<FName, TSoftObjectPtr<UAnimSequence>> ImportedAnimations;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TMap<FName, FWarAbilityPresentation> AbilityPresentations;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") FName AnimationStyle;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") float BasicContactSeconds = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TMap<FName, float> LocomotionSpeeds;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Equipment") TSoftObjectPtr<UStaticMesh> WeaponMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Equipment") TSoftObjectPtr<UStaticMesh> ShieldMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Equipment") FTransform WeaponGrip;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Equipment") FTransform ShieldGrip;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Equipment") FTransform WeaponStowed;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Equipment") FTransform ShieldStowed;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") FTransform MeshTransform = FTransform::Identity;

    UFUNCTION(BlueprintCallable, Category="Validation")
    bool ValidateForSpawn(EWarRealm ExpectedRealm, FString& OutError) const;
    FName GetSourceProfileKey() const { return SourceProfileKey.IsNone() ? ProfileKey : SourceProfileKey; }
    /** NPC source reuse is allowed only for NPC visuals, never playable class substitutes. */
    bool HasPlayableSourceIdentity() const { return !ProfileKey.IsNone() && GetSourceProfileKey() == ProfileKey; }

    virtual FPrimaryAssetId GetPrimaryAssetId() const override;
#if WITH_EDITOR
    virtual EDataValidationResult IsDataValid(FDataValidationContext& Context) const override;
#endif
};
