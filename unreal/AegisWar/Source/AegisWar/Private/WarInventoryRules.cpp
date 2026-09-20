#include "WarInventoryRules.h"

namespace
{
    bool IsEquipmentSlot(const FName Slot)
    {
        static const TSet<FName> Slots = {TEXT("head"), TEXT("neck"), TEXT("shoulders"), TEXT("chest"),
            TEXT("hands"), TEXT("waist"), TEXT("legs"), TEXT("feet"), TEXT("back"), TEXT("tabard"),
            TEXT("mainHand"), TEXT("offHand")};
        return Slots.Contains(Slot);
    }

    bool ValidateItem(const FWarInventoryItem& Item, FString& Error)
    {
        if (Item.Key.IsNone() || Item.Quantity <= 0 || (!Item.EquipSlot.IsNone() && !IsEquipmentSlot(Item.EquipSlot)))
        {
            Error = TEXT("Invalid catalog-resolved inventory item.");
            return false;
        }
        return true;
    }
}

bool FWarInventoryItem::IsStackable() const
{
    return !bHasAffix && EquipSlot.IsNone() && Kind != TEXT("weapon") && Kind != TEXT("armor");
}

bool WarInventory::Validate(const TArray<FWarInventoryItem>& Inventory, FString& Error)
{
    Error.Reset();
    TSet<int32> Slots;
    for (const auto& Item : Inventory)
    {
        if (!ValidateItem(Item, Error)) return false;
        if (Item.Slot < 0 || Item.Slot >= Capacity || Slots.Contains(Item.Slot)
            || Item.Quantity > (Item.IsStackable() ? StackLimit : 1))
        {
            Error = TEXT("Invalid or duplicated bag slot or stack quantity.");
            return false;
        }
        Slots.Add(Item.Slot);
    }
    return true;
}

bool WarInventory::PlaceRewards(const TArray<FWarInventoryItem>& Inventory, const TArray<FWarInventoryItem>& Rewards,
    TArray<FWarInventoryItem>& Result, TArray<FWarInventoryItem>& Pending, FString& Error)
{
    // Validate before publishing outputs. Failure never partially consumes or grants items.
    if (!Validate(Inventory, Error)) return false;
    for (const auto& Reward : Rewards) if (!ValidateItem(Reward, Error)) return false;
    TArray<FWarInventoryItem> Next = Inventory;
    TArray<FWarInventoryItem> Deferred;
    TSet<int32> Used;
    for (const auto& Item : Next) Used.Add(Item.Slot);
    for (const auto& Reward : Rewards)
    {
        int32 Remaining = Reward.Quantity;
        if (Reward.IsStackable())
        {
            for (auto& Stack : Next)
            {
                if (Stack.Key != Reward.Key || Stack.bHasAffix || !Stack.EquipSlot.IsNone() || Stack.Quantity >= StackLimit) continue;
                const int32 Amount = FMath::Min(StackLimit - Stack.Quantity, Remaining);
                Stack.Quantity += Amount;
                Remaining -= Amount;
                if (Remaining == 0) break;
            }
        }
        for (int32 Slot = 0; Slot < Capacity && Remaining > 0; ++Slot)
        {
            if (Used.Contains(Slot)) continue;
            FWarInventoryItem Added = Reward;
            Added.Slot = Slot;
            Added.Quantity = Reward.IsStackable() ? FMath::Min(StackLimit, Remaining) : 1;
            Next.Add(Added);
            Used.Add(Slot);
            Remaining -= Added.Quantity;
        }
        if (Remaining > 0)
        {
            FWarInventoryItem Remainder = Reward;
            Remainder.Slot = INDEX_NONE;
            Remainder.Quantity = Remaining;
            Deferred.Add(Remainder);
        }
    }
    Result = MoveTemp(Next);
    Pending = MoveTemp(Deferred);
    return true;
}

bool WarInventory::Equip(const TArray<FWarInventoryItem>& Inventory, const int32 BagSlot,
    TMap<FName, int32>& Equipment, FString& Error)
{
    if (!Validate(Inventory, Error)) return false;
    const auto* Item = Inventory.FindByPredicate([BagSlot](const auto& Row) { return Row.Slot == BagSlot; });
    if (!Item || !IsEquipmentSlot(Item->EquipSlot))
    {
        Error = TEXT("The selected bag item cannot be equipped.");
        return false;
    }
    Equipment.Add(Item->EquipSlot, BagSlot);
    return true;
}

bool WarInventory::StrengthBonus(const TArray<FWarInventoryItem>& Inventory, const TMap<FName, int32>& Equipment,
    int32& Result, FString& Error)
{
    if (!Validate(Inventory, Error)) return false;
    int64 Total = 0;
    for (const auto& Entry : Equipment)
    {
        const auto* Item = Inventory.FindByPredicate([&Entry](const auto& Row) { return Row.Slot == Entry.Value; });
        if (!IsEquipmentSlot(Entry.Key) || !Item || Item->EquipSlot != Entry.Key)
        {
            Error = TEXT("Equipped item no longer matches its bag slot.");
            return false;
        }
        if (Item->bHasAffix) Total += Item->StrengthBonus;
    }
    if (Total < MIN_int32 || Total > MAX_int32) { Error = TEXT("Equipment stat overflow."); return false; }
    Result = static_cast<int32>(Total);
    return true;
}
