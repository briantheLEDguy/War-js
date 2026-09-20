#include "WarTypes.h"

bool WarValidation::IsSha256(const FString& Value)
{
    if (Value.Len() != 64) return false;
    for (const TCHAR Character : Value)
    {
        if (!FChar::IsHexDigit(Character)) return false;
    }
    return true;
}

bool WarValidation::CanStrike(const EWarRealm Attacker, const EWarRealm Target,
    const float AttackerHealth, const float TargetHealth, const double DistanceSquared,
    const bool bLineOfSight, const bool bSameActor)
{
    return (Attacker == EWarRealm::Aegis || Attacker == EWarRealm::Riftbound)
        && (Target == EWarRealm::Aegis || Target == EWarRealm::Riftbound)
        && Attacker != Target && !bSameActor && bLineOfSight
        && FMath::IsFinite(AttackerHealth) && AttackerHealth > 0.f
        && FMath::IsFinite(TargetHealth) && TargetHealth > 0.f
        && FMath::IsFinite(DistanceSquared) && DistanceSquared >= 0.0
        && DistanceSquared <= FMath::Square(static_cast<double>(StrikeRangeCm));
}

bool WarValidation::AllowsDevelopmentNetwork(const bool bShipping, const bool bExplicitDevelopmentFlag)
{
    return !bShipping && bExplicitDevelopmentFlag;
}
