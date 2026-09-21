#pragma once
#include "CoreMinimal.h"
#include "WarQuestRules.h"

enum class EWarQuestMarker : uint8 { None, Offer, TurnIn };

/** Presentation query over one character's private progress; never changes quest state. */
namespace WarQuestMarkers
{
    AEGISWAR_API EWarQuestMarker Resolve(const TArray<FWarQuestDefinition>& Definitions,
        const TArray<FWarQuestProgress>& Progress, FName Realm, FName Zone, FName Npc, int32 Level);
}
