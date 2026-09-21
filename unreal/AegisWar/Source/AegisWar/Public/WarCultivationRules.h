#pragma once
#include "CoreMinimal.h"
#include "WarInventorySnapshot.h"

struct AEGISWAR_API FWarCultivationSeed
{
    FName Key;
    FString Name;
    int32 DurationMs = 0;
    int32 Xp = 0;
    int32 SlotLimit = 0;
    FName Additive;
    TArray<FWarInventoryItem> Outputs;
    TArray<FWarInventoryItem> BonusOutputs;
};

namespace WarCultivation
{
    // Pure transactions: failure leaves the snapshot unchanged. Callers supply trusted server time/catalog.
    AEGISWAR_API bool Plant(FWarInventorySnapshot& Inventory, const FWarCultivationSeed& Seed,
        bool bUseSoil, int64 NowMs, FGuid PlotId, FString& Error);
    AEGISWAR_API bool Harvest(FWarInventorySnapshot& Inventory, const FWarCultivationSeed& Seed,
        FGuid PlotId, int64 NowMs, FString& Error);
}
