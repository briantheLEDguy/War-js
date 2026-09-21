#pragma once
#include "CoreMinimal.h"

/** Local intent only; CharacterMovement still predicts and validates movement. */
struct AEGISWAR_API FWarMovementInput
{
    bool bAutoRun = false;
    void Toggle(bool bAllowed) { if (bAllowed) bAutoRun = !bAutoRun; }
    FVector2D Resolve(double Forward, double Right, bool bManualKey, bool bBothMouseButtons,
        bool bAllowed, bool bDeadOrFlying);
};
