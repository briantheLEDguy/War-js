#include "WarMovementInput.h"

FVector2D FWarMovementInput::Resolve(double Forward, double Right, bool bManualKey,
    bool bBothMouseButtons, bool bAllowed, bool bDeadOrFlying)
{
    if (bDeadOrFlying) bAutoRun = false;
    if (!bAllowed || !FMath::IsFinite(Forward) || !FMath::IsFinite(Right)) return FVector2D::ZeroVector;
    // Opposing held keys still cancel autorun even when their axes sum to zero.
    if (bManualKey) bAutoRun = false;
    FVector2D Intent(FMath::Clamp(Forward, -1.0, 1.0) + (bAutoRun ? 1.0 : 0.0)
        + (bBothMouseButtons ? 1.0 : 0.0), FMath::Clamp(Right, -1.0, 1.0));
    const double Length = Intent.Size();
    return Length > 1.0 ? Intent / Length : Intent;
}
