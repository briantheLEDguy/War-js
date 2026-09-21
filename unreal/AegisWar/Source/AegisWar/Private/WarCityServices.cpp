#include "WarCityServices.h"

FName WarCityServices::ServiceForNpc(const FName Npc)
{
    if (Npc == TEXT("aegis_capital_quartermaster")) return TEXT("quartermaster");
    if (Npc == TEXT("lantern_supply_merchant")) return TEXT("supplies");
    if (Npc == TEXT("aegis_capital_class_trainer")) return TEXT("class_teacher");
    if (Npc == TEXT("aegis_capital_craft_trainer")) return TEXT("craft_teacher");
    if (Npc == TEXT("aegis_capital_banker")) return TEXT("vault_keeper");
    return NAME_None;
}

TMap<FName, int32> WarCityServices::Offers(const FName Service)
{
    if (Service == TEXT("quartermaster")) return {{TEXT("bread"),2},{TEXT("potion_health"),10},{TEXT("potion_mana"),10}};
    if (Service == TEXT("supplies")) return {{TEXT("craft_scrap_iron"),4},{TEXT("craft_torn_cloth"),4},{TEXT("craft_clear_water"),2}};
    return {};
}

bool WarCityServices::Trade(const FWarInventorySnapshot& Current, const FWarInventoryItem& CatalogItem,
    const int32 Price, const bool bSell, const int32 Quantity, const int32 BagSlot,
    FWarInventorySnapshot& Next, FString& Error)
{
    Error = TEXT("Invalid merchant transaction.");
    if (Price < 2 || Quantity < 1 || Quantity > WarInventory::StackLimit || Current.Revision == MAX_int32
        || Current.CharacterProgression.Gold < 0 || !CatalogItem.IsStackable() || CatalogItem.Key.IsNone()) return false;
    const int64 Total = static_cast<int64>(bSell ? Price / 2 : Price) * Quantity;
    auto Candidate = Current;
    if (bSell)
    {
        auto* Item = Candidate.Items.FindByPredicate([BagSlot](const auto& Row) { return Row.Slot == BagSlot; });
        if (!Item || Item->Key != CatalogItem.Key || !Item->IsStackable() || Item->Quantity < Quantity
            || Current.Equipment.ContainsByPredicate([BagSlot](const auto& Row) { return Row.BagSlot == BagSlot; }))
        { Error = TEXT("Select an unequipped stack sold by this merchant."); return false; }
        if (Current.CharacterProgression.Gold > MAX_int64 - Total) return false;
        Item->Quantity -= Quantity;
        Candidate.Items.RemoveAll([](const auto& Row) { return Row.Quantity == 0; });
        Candidate.CharacterProgression.Gold += Total;
    }
    else
    {
        if (Current.CharacterProgression.Gold < Total) { Error = TEXT("Not enough gold."); return false; }
        auto Bought = CatalogItem; Bought.Quantity = Quantity;
        TArray<FWarInventoryItem> Items, Overflow;
        if (!WarInventory::PlaceRewards(Current.Items, {Bought}, Items, Overflow, Error)) return false;
        if (!Overflow.IsEmpty()) { Error = TEXT("Inventory full."); return false; }
        Candidate.Items = MoveTemp(Items);
        Candidate.CharacterProgression.Gold -= Total;
    }
    TArray<FWarInventoryItem> Delivered, Pending;
    if (!WarInventory::PlaceRewards(Candidate.Items, Candidate.PendingRewards, Delivered, Pending, Error)) return false;
    Candidate.Items = MoveTemp(Delivered); Candidate.PendingRewards = MoveTemp(Pending);
    ++Candidate.Revision;
    Next = MoveTemp(Candidate); Error.Reset(); return true;
}
