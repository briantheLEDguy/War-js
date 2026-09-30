#include "WarImpactCameraModifier.h"
#include "Camera/CameraTypes.h"

bool UWarImpactCameraModifier::ModifyCamera(float DeltaTime,FMinimalViewInfo& View)
{
    Remaining=FMath::Max(0.f,Remaining-DeltaTime);
    if (Remaining>0)
    {
        const float Envelope=FMath::Square(Remaining/.18f)*Strength;
        View.Rotation.Pitch+=FMath::Sin((.18f-Remaining)*95.f)*Envelope*.65f;
        View.Rotation.Roll+=FMath::Sin((.18f-Remaining)*71.f)*Envelope*.35f;
    }
    return false;
}
