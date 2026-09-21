#pragma once

#include "CoreMinimal.h"
#include "WarInventoryRules.h"
#include "WarInventorySnapshot.generated.h"

USTRUCT(BlueprintType)
struct AEGISWAR_API FWarEquipmentReference
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Slot;
    UPROPERTY(BlueprintReadOnly) int32 BagSlot = INDEX_NONE;
};

USTRUCT(BlueprintType)
struct AEGISWAR_API FWarProfessionProgress
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Profession;
    UPROPERTY(BlueprintReadOnly) int32 Xp = 0;
};

/** One owner-only replication unit; equipment never removes items from the bag. */
USTRUCT(BlueprintType)
struct AEGISWAR_API FWarInventorySnapshot
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 Revision = 0;
    UPROPERTY(BlueprintReadOnly) TArray<FWarInventoryItem> Items;
    UPROPERTY(BlueprintReadOnly) TArray<FWarInventoryItem> PendingRewards;
    UPROPERTY(BlueprintReadOnly) TArray<FWarEquipmentReference> Equipment;
    UPROPERTY(BlueprintReadOnly) TArray<FWarProfessionProgress> Professions;
};
