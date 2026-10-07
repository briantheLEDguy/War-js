#pragma once
#include "CoreMinimal.h"

/** Conservative steering reservations; authoritative equipment sweeps remain unchanged. */
struct FWarSiegeEscortHull
{
    FVector Center;
    FQuat Rotation;
    FVector Extent;
};
namespace WarSiegeEscort
{
    AEGISWAR_API FVector Offset(int32 Seat,float Yaw);
    AEGISWAR_API bool PointClear(const FVector& CapsuleCenter,TConstArrayView<FWarSiegeEscortHull> Hulls,float Radius,float HalfHeight);
    /** An initially obstructed pawn may leave monotonically; no path may enter or re-enter a reservation. */
    AEGISWAR_API bool PathClear(TConstArrayView<FVector> FloorPath,TConstArrayView<FWarSiegeEscortHull> Hulls,float Radius,float HalfHeight);
}
