#pragma once
#include "CoreMinimal.h"
class ACharacter;
class AActor;
class UWorld;
class UNavigationQueryFilter;
namespace WarSiegeNavigation
{
    /** Only actors owned by a v2 encounter use its expanded, bounded search. */
    AEGISWAR_API TSubclassOf<UNavigationQueryFilter> FilterFor(const AActor* Actor);
    /** Reachable, capsule-clear ground within the objective; never teleports a unit. */
    AEGISWAR_API bool Approach(const ACharacter* Pawn, const FVector& Anchor, const FVector& PreferredOffset, float CaptureRadius, FVector& Ground);
    AEGISWAR_API bool Detour(const ACharacter* Pawn, const FVector& Goal, float Side, FVector& Ground);
    /** Spawn checks include other pawns; ordinary approach checks leave those to crowd avoidance. */
    AEGISWAR_API bool SpawnCandidate(UWorld* World,const FVector& Ground,float Radius,float HalfHeight,FVector& Center,const AActor* Ignore = nullptr);
    AEGISWAR_API bool SpawnCenter(UWorld* World,const FVector& Anchor,FVector& Center,const ACharacter* Avatar = nullptr);
}
