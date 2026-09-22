#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarCombatPresentation.generated.h"

class UAnimSequence;
class USkeletalMeshComponent;
class UProceduralMeshComponent;
class UMaterialInterface;

UENUM(BlueprintType)
enum class EWarMagicTheme : uint8 { Gold, Fire, Violet };

/** A review cue is presentation only; it cannot apply damage or grant an ability. */
USTRUCT(BlueprintType)
struct FWarCombatPresentationCue
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> Animation;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) EWarMagicTheme Theme = EWarMagicTheme::Gold;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName EmitterBone = TEXT("hand_L");
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ReleaseSeconds = .6f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float TrailStart = .4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float TrailEnd = .8f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bWeapon = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bProjectile = false;
};

namespace WarCombatPresentation
{
    AEGISWAR_API float Charge(float Time, float Release);
    AEGISWAR_API float Afterglow(float Time, float Release, float Lifetime);
    AEGISWAR_API bool ValidTiming(float Duration, float Release, float Start, float End);
}

/** Isolated native art review actor; real skinned poses drive every effect anchor. */
UCLASS()
class AEGISWAR_API AWarCombatPresentation : public AActor
{
    GENERATED_BODY()
public:
    AWarCombatPresentation();
    virtual void Tick(float DeltaSeconds) override;
    virtual void BeginPlay() override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UProceduralMeshComponent> Effects;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UMaterialInterface> EffectMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FWarCombatPresentationCue Cue;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bLoopReview = true;
    /** Replay from zero for deterministic inspection of hand history and release origin. */
    UFUNCTION(BlueprintCallable, CallInEditor) bool ReviewAtTime(float Seconds);
    UFUNCTION(BlueprintCallable) bool IsCueValid() const;
private:
    struct FTrailSample { FVector Tip, Base; float Time; };
    TArray<FTrailSample> Trail;
    FVector ReleaseOrigin = FVector::ZeroVector;
    float Elapsed = 0.f;
    bool bReleased = false;
    void Sample(float Seconds);
    void DrawEffects(float Seconds);
};
