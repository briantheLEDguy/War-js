#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "WarTypes.h"
#include "WarCharacterVisualDefinition.generated.h"

class USkeletalMesh;
class UAnimInstance;
class UAnimSequence;

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
