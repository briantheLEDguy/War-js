#pragma once
#include "CoreMinimal.h"

namespace WarTargetReticle
{
    inline FLinearColor Color(bool bEnemy)
    {
        return bEnemy ? FLinearColor(1.f, .08f, .06f) : FLinearColor(.08f, .45f, 1.f);
    }

    // Fixed screen-space stroke and bounded corner lengths stay legible at any distance.
    inline TArray<TPair<FVector2D, FVector2D>> Corners(const FBox2D& Bounds, float Scale)
    {
        if (!Bounds.bIsValid || Bounds.GetSize().X <= 0 || Bounds.GetSize().Y <= 0) return {};
        const double Length = FMath::Min(24.0 * Scale, FMath::Min(Bounds.GetSize().X, Bounds.GetSize().Y) * .3);
        TArray<TPair<FVector2D, FVector2D>> Lines;
        for (int32 X = 0; X < 2; ++X) for (int32 Y = 0; Y < 2; ++Y)
        {
            const FVector2D Corner(X ? Bounds.Max.X : Bounds.Min.X, Y ? Bounds.Max.Y : Bounds.Min.Y);
            Lines.Emplace(Corner, Corner + FVector2D(X ? -Length : Length, 0));
            Lines.Emplace(Corner, Corner + FVector2D(0, Y ? -Length : Length));
        }
        return Lines;
    }
}
