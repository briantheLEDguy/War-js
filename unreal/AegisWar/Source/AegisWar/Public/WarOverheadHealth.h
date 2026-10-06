#pragma once
#include "CoreMinimal.h"

class AActor;
class AWarPlayerController;

struct FWarOverheadHealth
{
    float Fraction = 0;
    bool bEnemy = false;
};

namespace WarOverheadHealth
{
    constexpr float Width = 84.f, Height = 10.f, CombatTextLift = 12.f;
    /** Reads current replicated vitals; selection and outgoing combat notices are irrelevant. */
    AEGISWAR_API bool Read(const AWarPlayerController* Viewer, const AActor* Recipient, FWarOverheadHealth& Out);
    /** Invalid/offscreen rectangles draw nothing rather than pinning to the viewport edge. */
    AEGISWAR_API FBox2D Bounds(FVector2D Head, FVector2D Viewport, float Scale);
}
