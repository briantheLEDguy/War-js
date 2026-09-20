#pragma once

#include "CoreMinimal.h"
#include "WarTypes.generated.h"

UENUM(BlueprintType)
enum class EWarRealm : uint8
{
    None,
    Aegis,
    Riftbound
};

namespace WarValidation
{
    AEGISWAR_API bool IsSha256(const FString& Value);
    AEGISWAR_API bool CanStrike(EWarRealm Attacker, EWarRealm Target, float AttackerHealth,
        float TargetHealth, double DistanceSquared, bool bLineOfSight, bool bSameActor);
    AEGISWAR_API bool AllowsDevelopmentNetwork(bool bShipping, bool bExplicitDevelopmentFlag);
    constexpr float StrikeRangeCm = 300.f;
    constexpr float StrikeManaCost = 10.f;
    constexpr float StrikeDamage = 20.f;
    constexpr float StrikeCooldownSeconds = 2.f;
}
