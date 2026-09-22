#pragma once
#include "CoreMinimal.h"
#include "Engine/World.h"

namespace WarGmRules
{
    inline bool AllowsDevelopmentSession(bool bShipping, ENetMode NetMode, EWorldType::Type WorldType,
        bool bLocalEnabled, bool bExplicitLaunch)
    {
        return !bShipping && NetMode == NM_Standalone
            && (WorldType == EWorldType::PIE
                || (WorldType == EWorldType::Game && (bLocalEnabled || bExplicitLaunch)));
    }

    inline bool ValidCharacterQuery(const FString& Value)
    {
        const FString Name = Value.TrimStartAndEnd();
        return !Name.IsEmpty() && Name.Len() <= 32 && !Name.Contains(TEXT("\n")) && !Name.Contains(TEXT("\r"));
    }
    inline bool IsSafeLandingNormal(const FVector& Normal)
    { return !Normal.ContainsNaN() && Normal.Z >= 0.7; }
}
