#include "WarCultivationRules.h"
#include "WarCraftingRules.h"

bool WarCultivation::Plant(FWarInventorySnapshot& Inventory, const FWarCultivationSeed& Seed,
    const bool bUseSoil, const int64 NowMs, const FGuid PlotId, FString& Error)
{
    Error.Reset();
    if (Seed.Key.IsNone() || Seed.DurationMs <= 0 || Seed.SlotLimit <= 0 || NowMs < 0
        || NowMs > MAX_int64 - Seed.DurationMs || !PlotId.IsValid() || Inventory.Revision == MAX_int32
        || Inventory.CultivationPlots.Num() >= Seed.SlotLimit
        || Inventory.CultivationPlots.ContainsByPredicate([PlotId](const auto& Plot) { return Plot.Id == PlotId; }))
    { Error = TEXT("No cultivation slot is available or seed timing is invalid."); return false; }
    TMap<FName, int32> Inputs;
    Inputs.Add(Seed.Key, 1);
    if (bUseSoil && !Seed.Additive.IsNone()) Inputs.FindOrAdd(Seed.Additive) += 1;
    TMap<int32, int32> Consumed;
    if (!WarCrafting::SelectInputs(Inputs, Inventory.Items, Consumed, Error)) return false;
    auto Next = Inventory;
    for (const auto& Entry : Consumed)
    {
        if (Inventory.Equipment.ContainsByPredicate([&Entry](const auto& Gear) { return Gear.BagSlot == Entry.Key; }))
        { Error = TEXT("Equipped items cannot be planted."); return false; }
        Next.Items.FindByPredicate([&Entry](const auto& Item) { return Item.Slot == Entry.Key; })->Quantity -= Entry.Value;
    }
    Next.Items.RemoveAll([](const auto& Item) { return Item.Quantity == 0; });
    TArray<FWarInventoryItem> Delivered, Pending;
    if (!WarInventory::PlaceRewards(Next.Items, Next.PendingRewards, Delivered, Pending, Error)) return false;
    Next.Items = MoveTemp(Delivered); Next.PendingRewards = MoveTemp(Pending);
    FWarCultivationPlot Plot;
    Plot.Id = PlotId; Plot.SeedKey = Seed.Key; Plot.PlantedAtMs = NowMs; Plot.ReadyAtMs = NowMs + Seed.DurationMs;
    if (bUseSoil) Plot.Additive = Seed.Additive;
    Next.CultivationPlots.Add(Plot);
    ++Next.Revision;
    Inventory = MoveTemp(Next);
    return true;
}

bool WarCultivation::Harvest(FWarInventorySnapshot& Inventory, const FWarCultivationSeed& Seed,
    const FGuid PlotId, const int64 NowMs, FString& Error)
{
    Error.Reset();
    const auto* Plot = Inventory.CultivationPlots.FindByPredicate([PlotId](const auto& Row) { return Row.Id == PlotId; });
    if (!Plot || !PlotId.IsValid() || Plot->SeedKey != Seed.Key || NowMs < Plot->ReadyAtMs
        || Plot->ReadyAtMs < Plot->PlantedAtMs || Seed.Xp < 0 || Seed.Outputs.IsEmpty() || Inventory.Revision == MAX_int32)
    { Error = TEXT("This crop is missing, invalid or still growing."); return false; }
    const FName Profession(TEXT("cultivation"));
    const auto* Progress = Inventory.Professions.FindByPredicate([Profession](const auto& Row) { return Row.Profession == Profession; });
    const int32 PreviousXp = Progress ? Progress->Xp : 0;
    if (PreviousXp < 0 || PreviousXp > MAX_int32 - Seed.Xp)
    { Error = TEXT("Profession XP exceeds the supported range."); return false; }
    auto Rewards = Seed.Outputs;
    if (!Seed.Additive.IsNone() && Plot->Additive == Seed.Additive) Rewards.Append(Seed.BonusOutputs);
    TArray<FWarInventoryItem> Items, Overflow;
    if (!WarInventory::PlaceRewards(Inventory.Items, Rewards, Items, Overflow, Error)) return false;
    if (!Overflow.IsEmpty()) { Error = TEXT("Inventory full. Your crop remains ready to harvest."); return false; }
    auto Next = Inventory;
    if (!WarInventory::PlaceRewards(Items, Inventory.PendingRewards, Next.Items, Next.PendingRewards, Error)) return false;
    Next.CultivationPlots.RemoveAll([PlotId](const auto& Row) { return Row.Id == PlotId; });
    auto* Updated = Next.Professions.FindByPredicate([Profession](const auto& Row) { return Row.Profession == Profession; });
    if (!Updated) { FWarProfessionProgress Added; Added.Profession = Profession; Next.Professions.Add(Added); Updated = &Next.Professions.Last(); }
    Updated->Xp = PreviousXp + Seed.Xp;
    ++Next.Revision;
    Inventory = MoveTemp(Next);
    return true;
}
