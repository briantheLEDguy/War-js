#pragma once
#include "CoreMinimal.h"

namespace WarInterface
{
    // North is +X in the native world. Keep player and landmark projections identical.
    inline FVector2D MapPoint(FVector Position, FVector Centre, double Radius, FVector2D Size)
    {
        if (!FMath::IsFinite(Radius) || Radius <= 0 || Position.ContainsNaN() || Centre.ContainsNaN()) return Size * 0.5;
        return FVector2D(Size.X * (0.5 + (Position.Y - Centre.Y) / (2 * Radius)),
            Size.Y * (0.5 - (Position.X - Centre.X) / (2 * Radius)));
    }
    inline float SafeFrameLimit(float Value)
    {
        return FMath::IsFinite(Value) ? FMath::Clamp(Value, 30.f, 240.f) : 60.f;
    }
}
