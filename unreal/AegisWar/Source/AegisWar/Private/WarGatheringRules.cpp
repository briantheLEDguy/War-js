#include "WarGatheringRules.h"

bool WarGathering::IsAvailable(const FWarInventorySnapshot& Inventory, const FName ZoneId, const FName NodeId, const int64 NowMs)
{
    return !Inventory.ResourceCooldowns.ContainsByPredicate([=](const auto& Entry) {
        return Entry.ZoneId == ZoneId && Entry.NodeId == NodeId && Entry.AvailableAtMs > NowMs;
    });
}

bool WarGathering::Gather(FWarInventorySnapshot& Inventory, const FWarResourceDefinition& Node,
    const int64 NowMs, FRandomStream& Random, FString& Error)
{
    Error.Reset();
    if (Node.ZoneId.IsNone() || Node.NodeId.IsNone() || Node.Profession.IsNone() || Node.Xp < 0
        || Node.CooldownMs < 1000 || NowMs < 0 || NowMs > MAX_int64 - Node.CooldownMs || Node.Loot.IsEmpty()
        || Inventory.Revision == MAX_int32 || !IsAvailable(Inventory, Node.ZoneId, Node.NodeId, NowMs))
    { Error = TEXT("Resource node is unavailable or still recovering."); return false; }
    const auto* Progress = Inventory.Professions.FindByPredicate([&Node](const auto& Row) { return Row.Profession == Node.Profession; });
    const int32 PreviousXp = Progress ? Progress->Xp : 0;
    if (PreviousXp < 0 || PreviousXp > MAX_int32 - Node.Xp)
    { Error = TEXT("Profession XP exceeds the supported range."); return false; }
    TArray<FWarInventoryItem> Rewards;
    for (const auto& Entry : Node.Loot)
    {
        if (!FMath::IsFinite(Entry.Chance) || Entry.Chance < 0 || Entry.Chance > 1
            || Entry.MinimumQuantity <= 0 || Entry.MaximumQuantity < Entry.MinimumQuantity
            || int64(Entry.MaximumQuantity) - Entry.MinimumQuantity + 1 > MAX_int32 || Entry.Item.Quantity <= 0)
        { Error = TEXT("Invalid gathering loot definition."); return false; }
        if (Random.GetFraction() > Entry.Chance) continue;
        auto Item = Entry.Item;
        Item.Quantity = Random.RandRange(Entry.MinimumQuantity, Entry.MaximumQuantity);
        Rewards.Add(Item);
    }
    // The browser guarantees the first entry's base quantity when every probability roll misses.
    if (Rewards.IsEmpty()) Rewards.Add(Node.Loot[0].Item);
    TArray<FWarInventoryItem> Items, Overflow;
    if (!WarInventory::PlaceRewards(Inventory.Items, Rewards, Items, Overflow, Error)) return false;
    if (!Overflow.IsEmpty()) { Error = TEXT("Inventory full. Resource node remains available."); return false; }
    auto Next = Inventory;
    if (!WarInventory::PlaceRewards(Items, Inventory.PendingRewards, Next.Items, Next.PendingRewards, Error)) return false;
    Next.ResourceCooldowns.RemoveAll([NowMs](const auto& Entry) { return Entry.AvailableAtMs <= NowMs; });
    FWarResourceCooldown Cooldown; Cooldown.ZoneId = Node.ZoneId; Cooldown.NodeId = Node.NodeId; Cooldown.AvailableAtMs = NowMs + Node.CooldownMs;
    Next.ResourceCooldowns.Add(Cooldown);
    auto* Updated = Next.Professions.FindByPredicate([&Node](const auto& Row) { return Row.Profession == Node.Profession; });
    if (!Updated) { FWarProfessionProgress Added; Added.Profession = Node.Profession; Next.Professions.Add(Added); Updated = &Next.Professions.Last(); }
    Updated->Xp = PreviousXp + Node.Xp;
    ++Next.Revision;
    Inventory = MoveTemp(Next);
    return true;
}
