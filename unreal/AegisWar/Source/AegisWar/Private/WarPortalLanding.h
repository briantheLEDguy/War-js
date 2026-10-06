#pragma once
#include "CoreMinimal.h"

class AWarCharacter;
class AWarZoneAnchor;

namespace WarPortalLanding
{
    /** Exact arrival for normal travel; bounded, connected ground for evacuation crowds. */
    bool Find(AWarCharacter* Character,const FVector& Arrival,const AWarZoneAnchor* Zone,
        float SearchRadius,const AActor* Source,const AActor* Destination,FVector& Landing,FString& Error);
}
