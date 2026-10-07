#pragma once
#include "CoreMinimal.h"
class ACharacter;
class AActor;
class UWorld;
class UNavigationQueryFilter;
class AWarSiegeEncounter;
struct FHitResult;
namespace WarSiegeNavigation
{
    /** Only actors owned by a v2 encounter use its expanded, bounded search. */
    AEGISWAR_API TSubclassOf<UNavigationQueryFilter> FilterFor(const AActor* Actor);
    /** Reachable, capsule-clear ground within the objective; never teleports a unit. */
    AEGISWAR_API bool Approach(const ACharacter* Pawn, const FVector& Anchor, const FVector& PreferredOffset, float CaptureRadius, FVector& Ground);
    AEGISWAR_API bool ConvoyApproach(const ACharacter* Pawn,const FVector& Anchor,const FVector& PreferredOffset,float CaptureRadius,const AWarSiegeEncounter* Encounter,FVector& Ground,bool bFormation);
    AEGISWAR_API bool ConvoyPositionClear(const ACharacter* Pawn,const AWarSiegeEncounter* Encounter);
    AEGISWAR_API bool ConvoyPathClear(const ACharacter* Pawn,const AWarSiegeEncounter* Encounter,TConstArrayView<FVector> FloorPath);
    AEGISWAR_API bool Detour(const ACharacter* Pawn, const FVector& Goal, float Side, FVector& Ground);
    /** Bind a rasterized nav point to the static floor directly below its XY; never change levels. */
    AEGISWAR_API bool ProjectedFloor(UWorld* World,const FVector& NavigationPoint,FHitResult& Floor,const AActor* Ignore = nullptr);
    /** Spawn checks include other pawns; ordinary approach checks leave those to crowd avoidance. */
    AEGISWAR_API bool SpawnCandidate(UWorld* World,const FVector& Ground,float Radius,float HalfHeight,FVector& Center,const AActor* Ignore = nullptr);
    AEGISWAR_API bool SpawnCenter(UWorld* World,const FVector& Anchor,FVector& Center,const ACharacter* Avatar = nullptr);
}
