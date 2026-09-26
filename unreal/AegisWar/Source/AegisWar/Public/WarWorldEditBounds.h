#pragma once
#include "CoreMinimal.h"

namespace WarWorldEditBounds
{
    // Capitals occupy separate world origins. Keep edits near their trusted
    // authored template instead of treating Aegis's origin as the whole world.
    inline bool InWorld(const FVector& Position)
    { return !Position.ContainsNaN() && Position.GetAbsMax() <= 10000000.; }

    inline bool NearTemplate(const FVector& Position, const FVector& Anchor)
    {
        if (!InWorld(Position) || !InWorld(Anchor)) return false;
        // Preserve the established Aegis draft boundary exactly.
        if (Anchor.GetAbsMax() <= 100000.) return Position.GetAbsMax() <= 100000.;
        return (Position-Anchor).GetAbsMax() <= 100000.;
    }
}
