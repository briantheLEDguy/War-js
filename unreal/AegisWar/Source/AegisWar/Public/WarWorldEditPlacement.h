#pragma once
#include "CoreMinimal.h"

namespace WarWorldEditPlacement
{
    // World XY is the construction grid; terrain tracing owns placement height.
    AEGISWAR_API FVector SnapHorizontal(FVector Position, double GridCentimeters);
    AEGISWAR_API FTransform SnapTransform(const FTransform& Transform, double GridCentimeters, double AngleDegrees);
    // Fields: XYZ metres, pitch/yaw/roll degrees, XYZ scale magnitudes.
    AEGISWAR_API TOptional<double> ComponentValue(const FTransform& Transform, int32 Field);
    AEGISWAR_API bool SetComponent(FTransform& Transform, int32 Field, double Value);
}
