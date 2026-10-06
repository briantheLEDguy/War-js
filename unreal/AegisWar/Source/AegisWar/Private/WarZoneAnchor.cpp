#include "WarZoneAnchor.h"
#include "WarCityDefinition.h"
#include "EngineUtils.h"

TArray<FName> AWarZoneAnchor::GetContentLevels() const
{
    TArray<FName> Result = ContentLevels;
    if (CityDefinition) Result.Append(CityDefinition->Packages());
    return Result;
}

bool AWarZoneAnchor::ValidateCity(FString& Error) const
{
    const bool Capital = ZoneId == TEXT("aegis_capital") || ZoneId == TEXT("riftspire_capital");
    if (!CityDefinition)
    {
        if (!Capital) return true;
        Error = TEXT("Shared city definition is missing. Restore city content and retry."); return false;
    }
    if (CityDefinition->ZoneId != ZoneId || !CityDefinition->Origin.Equals(ZoneOrigin))
    { Error = TEXT("Shared city identity or origin differs from campaign routing."); return false; }
    if (!CityDefinition->Validate(Error)) return false;
    TSet<FName> Seen;
    for (FName Package : GetContentLevels())
    {
        if (Seen.Contains(Package))
        { Error = TEXT("City scenery or gameplay is attached twice."); return false; }
        Seen.Add(Package);
    }
    return true;
}

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
