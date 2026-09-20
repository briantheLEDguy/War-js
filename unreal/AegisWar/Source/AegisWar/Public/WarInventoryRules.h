#pragma once

#include "CoreMinimal.h"
#include "WarInventoryRules.generated.h"

/** Catalog-resolved inventory data. Equipped items continue occupying their bag slot. */
USTRUCT(BlueprintType)
struct AEGISWAR_API FWarInventoryItem
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Key;
    UPROPERTY(BlueprintReadOnly) FName Kind;
    UPROPERTY(BlueprintReadOnly) FName EquipSlot;
    UPROPERTY(BlueprintReadOnly) int32 Slot = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) int32 Quantity = 1;
    UPROPERTY(BlueprintReadOnly) bool bHasAffix = false;
    UPROPERTY(BlueprintReadOnly) int32 StrengthBonus = 0;

    bool IsStackable() const;
};

/** Pure rules shared by trusted reward/crafting commands; these functions grant no client authority. */
namespace WarInventory
{
    inline constexpr int32 Capacity = 24;
    inline constexpr int32 StackLimit = 99;

    AEGISWAR_API bool Validate(const TArray<FWarInventoryItem>& Inventory, FString& Error);
    AEGISWAR_API bool PlaceRewards(const TArray<FWarInventoryItem>& Inventory, const TArray<FWarInventoryItem>& Rewards,
        TArray<FWarInventoryItem>& Result, TArray<FWarInventoryItem>& Pending, FString& Error);
    AEGISWAR_API bool Equip(const TArray<FWarInventoryItem>& Inventory, int32 BagSlot,
        TMap<FName, int32>& Equipment, FString& Error);
    AEGISWAR_API bool StrengthBonus(const TArray<FWarInventoryItem>& Inventory, const TMap<FName, int32>& Equipment,
        int32& Result, FString& Error);
}
