#include "WarZoneAnchor.h"
#include "EngineUtils.h"

bool AWarZoneAnchor::ContainsPoint(FVector Origin, double Extent, FVector Point)
{
    return !Origin.ContainsNaN() && !Point.ContainsNaN() && FMath::IsFinite(Extent) && Extent > 0
        && FMath::Abs(Point.X-Origin.X) <= Extent && FMath::Abs(Point.Y-Origin.Y) <= Extent;
}
AWarZoneAnchor* AWarZoneAnchor::FindAt(UWorld* World, FVector Point)
{
    if (!World) return nullptr;
    AWarZoneAnchor* Result = nullptr;
    for (TActorIterator<AWarZoneAnchor> It(World); It; ++It)
        if (ContainsPoint(It->ZoneOrigin, It->HalfSize, Point))
        { if (Result) return nullptr; Result = *It; }
    return Result;
}
AWarZoneAnchor* AWarZoneAnchor::FindById(UWorld* World, FName Id)
{
    if (!World || Id.IsNone()) return nullptr;
    AWarZoneAnchor* Result = nullptr;
    for (TActorIterator<AWarZoneAnchor> It(World); It; ++It)
        if (It->ZoneId == Id) { if (Result) return nullptr; Result = *It; }
    return Result;
}
