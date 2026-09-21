#pragma once

#include "CoreMinimal.h"
#include "WarInventorySnapshot.h"

struct AEGISWAR_API FWarQuestObjective
{
    FName Id;
    FString KillTarget;
    FString Description;
    FName ZoneId;
    int32 Required = 1;
};

struct AEGISWAR_API FWarQuestReward
{
    FWarInventoryItem Item;
    bool bRollStrength = false;
    int32 MinimumStrength = 0, MaximumStrength = 0;
};

struct AEGISWAR_API FWarQuestDefinition
{
    FName Id, Realm, GiverNpcId, GiverZoneId, TurninNpcId, TurninZoneId, Prerequisite;
    FString Title, Description;
    TArray<FWarQuestReward> Rewards;
    int32 MinLevel = 1;
    int32 Xp = 0, Gold = 0;
    TArray<FWarQuestObjective> Objectives;
};

/** Trusted server rules only. NPC identity/range and kill attribution must be verified by callers. */
namespace WarQuests
{
    AEGISWAR_API bool ResolveRewards(const FWarQuestDefinition& Quest, TFunctionRef<double()> RandomUnit,
        TArray<FWarInventoryItem>& Rewards, FString& Error);
    AEGISWAR_API bool Accept(const FWarQuestDefinition& Quest, FName Realm, FName Zone, int32 Level,
        TArray<FWarQuestProgress>& Progress, FString& Error);
    AEGISWAR_API bool Kill(const FWarQuestDefinition& Quest, FName Realm, FName Zone,
        const FString& EnemyName, TArray<FWarQuestProgress>& Progress);
    AEGISWAR_API bool TurnIn(const FWarQuestDefinition& Quest, FName Realm, FName Zone,
        const TArray<FWarInventoryItem>& ResolvedRewards, const FWarInventorySnapshot& Inventory,
        TArray<FWarQuestProgress>& Progress, FWarInventorySnapshot& Next, FString& Error);
}
