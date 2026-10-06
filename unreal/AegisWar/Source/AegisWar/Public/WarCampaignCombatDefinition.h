#pragma once
#include "CoreMinimal.h"
#include "WarAbilityCatalog.h"

/** Immutable applied values only. Cross-ability references are validated by the complete restore table. */
namespace WarCampaignCombatDefinition
{
    AEGISWAR_API bool Encode(const FWarAbilityDefinition& Definition, FString& Payload, FString& Sha256, FString& Error);
    AEGISWAR_API bool Decode(const FString& Payload, const FString& Sha256, FWarAbilityDefinition& Out, FString& Error);
}
