#include "WarCraftingRules.h"

int32 WarCrafting::RankForXp(const int32 Xp) { return FMath::Max(0, Xp) / 100 + 1; }

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
