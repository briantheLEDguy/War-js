#pragma once
#include "CoreMinimal.h"
#include "Camera/CameraModifier.h"
#include "WarImpactCameraModifier.generated.h"

/** Short cosmetic impulse applied to the view only, never control rotation or movement. */
UCLASS()
class AEGISWAR_API UWarImpactCameraModifier : public UCameraModifier
{
    GENERATED_BODY()
public:
    void Pulse(float Intensity) { Strength=FMath::Clamp(Intensity,0.f,1.f); Remaining=.18f; }
    void Stop() { Remaining=0; }
    virtual bool ModifyCamera(float DeltaTime, FMinimalViewInfo& InOutPOV) override;
private:
    float Remaining=0, Strength=0;
};
