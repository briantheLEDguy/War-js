#pragma once
#include "CoreMinimal.h"
class ACharacter;
class UWorld;
namespace WarSiegeNavigation
{
    /** Reachable, capsule-clear ground within the objective; never teleports a unit. */
    AEGISWAR_API bool Approach(const ACharacter* Pawn, const FVector& Anchor, const FVector& PreferredOffset, float CaptureRadius, FVector& Ground);
    /** Spawn checks include other pawns; ordinary approach checks leave those to crowd avoidance. */
    AEGISWAR_API bool SpawnCandidate(UWorld* World,const FVector& Ground,float Radius,float HalfHeight,FVector& Center);
    AEGISWAR_API bool SpawnCenter(UWorld* World,const FVector& Anchor,FVector& Center);
}
