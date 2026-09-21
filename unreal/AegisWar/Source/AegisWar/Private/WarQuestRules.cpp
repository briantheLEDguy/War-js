#include "WarQuestRules.h"

namespace
{
    bool Valid(const FWarQuestDefinition& Quest)
    {
        if (Quest.Id.IsNone() || Quest.MinLevel < 1 || Quest.Xp < 0 || Quest.Gold < 0 || Quest.Objectives.IsEmpty()) return false;
        TSet<FName> Ids;
        for (const auto& Objective : Quest.Objectives)
        {
            if (Objective.Id.IsNone() || Objective.KillTarget.IsEmpty() || Objective.Required < 1 || Ids.Contains(Objective.Id)) return false;
            Ids.Add(Objective.Id);
        }
        return true;
    }
    bool MatchesRealm(const FWarQuestDefinition& Quest, FName Realm)
    { return Quest.Realm.IsNone() || Quest.Realm == Realm; }
}

bool WarQuests::Accept(const FWarQuestDefinition& Quest, FName Realm, FName Zone, int32 Level,
    TArray<FWarQuestProgress>& Progress, FString& Error)
{
    Error.Reset();
    const auto* Own = Progress.FindByPredicate([&](const auto& Row) { return Row.Id == Quest.Id; });
    const bool bPrerequisite = Quest.Prerequisite.IsNone() || Progress.ContainsByPredicate([&](const auto& Row) {
        return Row.Id == Quest.Prerequisite && Row.Status == TEXT("completed"); });
    if (!Valid(Quest) || !MatchesRealm(Quest, Realm) || Level < Quest.MinLevel || !bPrerequisite
        || (!Quest.GiverZoneId.IsNone() && Quest.GiverZoneId != Zone) || (Own && Own->Status != TEXT("available")))
    { Error = TEXT("Quest is not available here for this character."); return false; }
    FWarQuestProgress Accepted; Accepted.Id = Quest.Id;
    for (const auto& Objective : Quest.Objectives) Accepted.SetCount(Objective.Id, 0);
    if (Own) Progress[Own - Progress.GetData()] = MoveTemp(Accepted);
    else Progress.Add(MoveTemp(Accepted));
    return true;
}

bool WarQuests::Kill(const FWarQuestDefinition& Quest, FName Realm, FName Zone, const FString& EnemyName,
    TArray<FWarQuestProgress>& Progress)
{
    if (!Valid(Quest) || !MatchesRealm(Quest, Realm)) return false;
    auto* Own = Progress.FindByPredicate([&](const auto& Row) { return Row.Id == Quest.Id; });
    if (!Own || Own->Status != TEXT("active")) return false;
    bool bChanged = false;
    for (const auto& Objective : Quest.Objectives)
    {
        if (Objective.KillTarget != EnemyName || (!Objective.ZoneId.IsNone() && Objective.ZoneId != Zone)) continue;
        const int32 Count = Own->GetCount(Objective.Id);
        if (Count < Objective.Required) { Own->SetCount(Objective.Id, Count + 1); bChanged = true; }
    }
    if (bChanged && !Quest.Objectives.ContainsByPredicate([&](const auto& Objective) {
        return Own->GetCount(Objective.Id) < Objective.Required; })) Own->Status = TEXT("ready_to_turn_in");
    return bChanged;
}

bool WarQuests::TurnIn(const FWarQuestDefinition& Quest, FName Realm, FName Zone,
    const TArray<FWarInventoryItem>& ResolvedRewards, const FWarInventorySnapshot& Inventory,
    TArray<FWarQuestProgress>& Progress, FWarInventorySnapshot& Next, FString& Error)
{
    Error.Reset();
    auto* Own = Progress.FindByPredicate([&](const auto& Row) { return Row.Id == Quest.Id; });
    const FName RequiredZone = Quest.TurninZoneId.IsNone() ? Quest.GiverZoneId : Quest.TurninZoneId;
    if (!Valid(Quest) || !MatchesRealm(Quest, Realm) || (!RequiredZone.IsNone() && RequiredZone != Zone)
        || !Own || Own->Status != TEXT("ready_to_turn_in") || Inventory.Revision < 0 || Inventory.Revision == MAX_int32
        || Quest.Objectives.ContainsByPredicate([&](const auto& Objective) { return Own->GetCount(Objective.Id) < Objective.Required; }))
    { Error = TEXT("Quest is not ready to complete here."); return false; }
    auto Result = Inventory;
    TArray<FWarInventoryItem> Pending;
    if (!WarInventory::PlaceRewards(Inventory.Items, ResolvedRewards, Result.Items, Pending, Error)) return false;
    if (!Pending.IsEmpty()) { Error = TEXT("Make room for all quest rewards."); return false; }
    if (!WarProgression::Award(Inventory.CharacterProgression, Quest.Xp, Quest.Gold, Result.CharacterProgression, Error)) return false;
    ++Result.Revision;
    // Do not deliver unrelated pending gear here: browser quest turn-in requires its own rewards to fit atomically.
    Next = MoveTemp(Result);
    Own->Status = TEXT("completed");
    return true;
}

bool WarQuests::ResolveRewards(const FWarQuestDefinition& Quest, TFunctionRef<double()> RandomUnit,
    TArray<FWarInventoryItem>& Rewards, FString& Error)
{
    Error.Reset(); TArray<FWarInventoryItem> Result;
    for (const auto& Reward : Quest.Rewards)
    {
        auto Item = Reward.Item;
        if (Item.Quantity <= 0) { Error = TEXT("Quest reward quantity is invalid."); return false; }
        auto Probe = Item; Probe.Quantity = 1; Probe.Slot = 0;
        if (!WarInventory::Validate({Probe}, Error)) return false;
        if (Reward.bRollStrength)
        {
            const int64 Width = int64(Reward.MaximumStrength) - Reward.MinimumStrength + 1;
            if (Reward.MinimumStrength < 0 || Width <= 0 || Width > MAX_int32)
            { Error = TEXT("Quest affix range is invalid."); return false; }
            const double Roll = RandomUnit();
            if (!FMath::IsFinite(Roll) || Roll < 0.0 || Roll >= 1.0)
            { Error = TEXT("Quest reward random sample is invalid."); return false; }
            Item.bHasAffix = true;
            Item.StrengthBonus = Reward.MinimumStrength + int32(FMath::FloorToDouble(Roll * double(Width)));
        }
        Result.Add(Item);
    }
    Rewards = MoveTemp(Result); return true;
}
