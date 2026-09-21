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
