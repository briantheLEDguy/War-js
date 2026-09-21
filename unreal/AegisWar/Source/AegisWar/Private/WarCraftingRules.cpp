#include "WarCraftingRules.h"

int32 WarCrafting::RankForXp(const int32 Xp) { return FMath::Max(0, Xp) / 100 + 1; }

bool WarCrafting::SalvageOutputs(const FWarInventoryItem& Item, TArray<FWarInventoryItem>& Outputs, FString& Error)
{
    Error.Reset();
    if ((Item.Kind != TEXT("weapon") && Item.Kind != TEXT("armor")) || Item.Quantity != 1
        || (Item.bHasAffix && Item.StrengthBonus < 0))
    { Error = TEXT("That item cannot be salvaged."); return false; }
    const int32 Strength = Item.bHasAffix ? Item.StrengthBonus : 0;
    TArray<FWarInventoryItem> Result;
    const auto Add = [&Result](const TCHAR* Key, const int32 Quantity) {
        FWarInventoryItem Output; Output.Key = Key; Output.Kind = TEXT("misc"); Output.Quantity = Quantity;
        Result.Add(Output);
    };
    if (Item.Kind == TEXT("weapon"))
    {
        Add(TEXT("craft_scrap_iron"), 2 + FMath::Min(2, Strength));
        Add(TEXT("craft_talisman_fragment"), 1);
    }
    else if (Item.EquipSlot == TEXT("chest") || Item.EquipSlot == TEXT("shoulders") || Item.EquipSlot == TEXT("legs"))
    {
        Add(TEXT("craft_scrap_iron"), 2);
        Add(TEXT("craft_torn_cloth"), 1 + FMath::Min(2, Strength));
    }
    else
    {
        Add(TEXT("craft_ragged_leather"), 2);
        Add(TEXT("craft_torn_cloth"), 1 + FMath::Min(1, Strength));
    }
    if (Strength >= 3) Add(TEXT("craft_essence_minor"), 1);
    Outputs = MoveTemp(Result);
    return true;
}

bool WarCrafting::SelectIngredients(const FWarCraftRecipe& Recipe, const FName Station, const int32 ProfessionXp,
    const TArray<FWarInventoryItem>& Inventory, TMap<int32, int32>& ConsumedSlots, FString& Error)
{
    if (!WarInventory::Validate(Inventory, Error)) return false;
    if (Recipe.Id.IsNone() || Recipe.Profession.IsNone() || Recipe.Station.IsNone() || Recipe.MinimumRank < 1
        || Recipe.Xp < 0 || Recipe.Inputs.IsEmpty() || Recipe.Outputs.IsEmpty())
    { Error = TEXT("Invalid crafting recipe."); return false; }
    if (!Station.IsNone() && Station != TEXT("general") && Station != Recipe.Station)
    { Error = TEXT("This recipe requires a different crafting station."); return false; }
    if (RankForXp(ProfessionXp) < Recipe.MinimumRank)
    { Error = TEXT("Profession rank is too low for this recipe."); return false; }
    auto Remaining = Recipe.Inputs;
    for (const auto& Entry : Remaining)
        if (Entry.Key.IsNone() || Entry.Value <= 0) { Error = TEXT("Invalid recipe ingredient."); return false; }
    TMap<int32, int32> Selected;
    for (const auto& Item : Inventory)
    {
        auto* Needed = Remaining.Find(Item.Key);
        if (!Needed || *Needed <= 0) continue;
        const int32 Amount = FMath::Min(*Needed, Item.Quantity);
        Selected.Add(Item.Slot, Amount);
        *Needed -= Amount;
    }
    for (const auto& Entry : Remaining)
        if (Entry.Value > 0) { Error = TEXT("Missing ingredients."); return false; }
    ConsumedSlots = MoveTemp(Selected);
    return true;
}
