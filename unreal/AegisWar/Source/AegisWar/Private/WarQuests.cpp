#include "WarPlayerState.h"
#include "WarQuestRules.h"

namespace
{
    FName QuestRealm(EWarRealm Realm)
    { return Realm == EWarRealm::Aegis ? FName(TEXT("aegis")) : Realm == EWarRealm::Riftbound ? FName(TEXT("riftbound")) : NAME_None; }
}

bool AWarPlayerState::AcceptQuestTrusted(const FWarQuestDefinition& Quest, FName Zone, int32 ExpectedRevision, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || Realm == EWarRealm::None || ExpectedRevision != Inventory.Revision || Inventory.Revision == MAX_int32)
    { Error = TEXT("Quest acceptance is unauthorized or character state changed."); return false; }
    if (!WarQuests::Accept(Quest, QuestRealm(Realm), Zone, Inventory.CharacterProgression.Level, Inventory.Quests, Error)) return false;
    ++Inventory.Revision; ForceNetUpdate(); return true;
}

bool AWarPlayerState::RecordQuestKillTrusted(const TArray<FWarQuestDefinition>& Quests, FName Zone,
    const FString& EnemyName, const FGuid& KillEvent, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || Realm == EWarRealm::None || !KillEvent.IsValid() || QuestKillReceipts.Contains(KillEvent)
        || QuestKillReceipts.Num() >= 65536 || Inventory.Revision == MAX_int32)
    { Error = TEXT("Quest kill event is unauthorized, duplicated or exceeds session limits."); return false; }
    bool Changed = false;
    TSet<FName> Seen;
    for (const auto& Quest : Quests)
    {
        if (Seen.Contains(Quest.Id)) { Error = TEXT("Quest catalog contains duplicate identities."); return false; }
        Seen.Add(Quest.Id);
    }
    for (const auto& Quest : Quests) Changed |= WarQuests::Kill(Quest, QuestRealm(Realm), Zone, EnemyName, Inventory.Quests);
    // Remember even unmatched events so a later acceptance cannot replay an old kill.
    QuestKillReceipts.Add(KillEvent);
    if (Changed) { ++Inventory.Revision; ForceNetUpdate(); }
    return true;
}

bool AWarPlayerState::CompleteQuestTrusted(const FWarQuestDefinition& Quest, FName Zone, int32 ExpectedRevision,
    const TArray<FWarInventoryItem>& ResolvedRewards, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || Realm == EWarRealm::None || ExpectedRevision != Inventory.Revision)
    { Error = TEXT("Quest completion is unauthorized or character state changed."); return false; }
    auto Progress = Inventory.Quests;
    FWarInventorySnapshot Next;
    if (!WarQuests::TurnIn(Quest, QuestRealm(Realm), Zone, ResolvedRewards, Inventory, Progress, Next, Error)) return false;
    const bool Leveled = Next.CharacterProgression.Level > Inventory.CharacterProgression.Level;
    Next.Quests = MoveTemp(Progress);
    Inventory = MoveTemp(Next);
    if (Leveled) ApplyProgressionVitals(true);
    ForceNetUpdate(); return true;
}
