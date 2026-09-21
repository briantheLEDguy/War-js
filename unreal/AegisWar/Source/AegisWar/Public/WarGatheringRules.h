#pragma once
#include "CoreMinimal.h"
#include "WarInventorySnapshot.h"

struct AEGISWAR_API FWarGatheringLoot
{
    FWarInventoryItem Item;
    double Chance = 0;
    int32 MinimumQuantity = 1;
    int32 MaximumQuantity = 1;
};
struct AEGISWAR_API FWarResourceDefinition
{
    FName ZoneId;
    FName NodeId;
    FName VisualPropId;
    FName Profession;
    FString Label;
    bool bMeasureHeight = false;
    float RadiusCm = 450.f;
    int64 CooldownMs = 1000;
    int32 Xp = 0;
    TArray<FWarGatheringLoot> Loot;
};
namespace WarGathering
{
    AEGISWAR_API bool IsAvailable(const FWarInventorySnapshot& Inventory, FName ZoneId, FName NodeId, int64 NowMs);
    // The server resolves the node and supplies time/randomness; no client-provided rewards are accepted.
    AEGISWAR_API bool Gather(FWarInventorySnapshot& Inventory, const FWarResourceDefinition& Node,
        int64 NowMs, FRandomStream& Random, FString& Error);
}
