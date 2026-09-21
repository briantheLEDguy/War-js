#pragma once
#include "CoreMinimal.h"
#include "WarInventorySnapshot.h"

namespace WarCityServices
{
    AEGISWAR_API FName ServiceForNpc(FName Npc);
    AEGISWAR_API TMap<FName, int32> Offers(FName Service);
    AEGISWAR_API bool Trade(const FWarInventorySnapshot& Current, const FWarInventoryItem& CatalogItem,
        int32 Price, bool bSell, int32 Quantity, int32 BagSlot, FWarInventorySnapshot& Next, FString& Error);
}
