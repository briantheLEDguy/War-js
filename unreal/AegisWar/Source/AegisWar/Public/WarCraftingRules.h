#pragma once

#include "CoreMinimal.h"
#include "WarInventoryRules.h"

struct AEGISWAR_API FWarCraftReward
{
    FWarInventoryItem Item;
    bool bRollStrength = false;
    int32 MinimumStrength = 0;
    int32 MaximumStrength = 0;
};

struct AEGISWAR_API FWarCraftRecipe
{
    FName Id;
    FName Profession;
    FName Station;
    FString Name;
    int32 MinimumRank = 1;
    int32 Xp = 0;
    TMap<FName, int32> Inputs;
    TArray<FWarCraftReward> Outputs;
};

namespace WarCrafting
{
    AEGISWAR_API int32 RankForXp(int32 Xp);
    AEGISWAR_API bool SalvageOutputs(const FWarInventoryItem& Item, TArray<FWarInventoryItem>& Outputs, FString& Error);
    AEGISWAR_API bool SelectIngredients(const FWarCraftRecipe& Recipe, FName Station, int32 ProfessionXp,
        const TArray<FWarInventoryItem>& Inventory, TMap<int32, int32>& ConsumedSlots, FString& Error);
}
