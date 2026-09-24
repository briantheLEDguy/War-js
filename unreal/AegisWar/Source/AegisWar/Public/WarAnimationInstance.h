#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "WarAnimationInstance.generated.h"

class UAnimSequence;

/** Native full-body state playback. Effects and capsule travel remain server-owned. */
UCLASS(Transient, BlueprintType)
class AEGISWAR_API UWarAnimationInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    void Select(UAnimSequence* Sequence, FName State, float Time, float BlendSeconds = .14f);
    void PreparePose(float DeltaSeconds);
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Current;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Previous;
    FName State;
    FName EvaluatedState;
    float EvaluatedTime = 0;
    double EvaluatedServerTime = -1;
    float CurrentTime = 0, PreviousTime = 0, Blend = 1, BlendDuration = .14f;
};
