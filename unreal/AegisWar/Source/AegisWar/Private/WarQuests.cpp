#include "WarPlayerState.h"
#include "WarQuestRules.h"
#include "WarContentSubsystem.h"
#include "WarQuestNpc.h"
#include "Engine/GameInstance.h"

namespace
{
    FName QuestRealm(EWarRealm Realm)
    { return Realm == EWarRealm::Aegis ? FName(TEXT("aegis")) : Realm == EWarRealm::Riftbound ? FName(TEXT("riftbound")) : NAME_None; }
}

bool AWarPlayerState::InteractQuest(const AWarQuestNpc* Npc, FName QuestId, bool bTurnIn, int32 ExpectedRevision, FString& Error)
{
    if (!HasAuthority() || !CanPerformInventoryAction() || ExpectedRevision != Inventory.Revision || !IsValid(Npc))
    { Error = TEXT("Quest interaction is unavailable or character state changed."); return false; }
    FString Name;
    if (!Npc->ResolveInteraction(GetPawn(), Name, Error)) return false;
    const auto* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    FWarQuestDefinition Quest;
    if (!Content || !Content->GetQuest(QuestId, Quest, Error)) return false;
    if ((bTurnIn ? Quest.TurninNpcId : Quest.GiverNpcId) != Npc->NpcId)
    { Error = TEXT("This character cannot perform that quest interaction."); return false; }
    return bTurnIn ? CompleteCatalogQuestTrusted(QuestId, Npc->ZoneId, ExpectedRevision, Error)
        : AcceptCatalogQuestTrusted(QuestId, Npc->ZoneId, ExpectedRevision, Error);
}
void AWarPlayerState::ServerInteractQuest_Implementation(AWarQuestNpc* Npc, FName QuestId, bool bTurnIn, int32 ExpectedRevision)
{
    FString Error; const bool Accepted = InteractQuest(Npc, QuestId, bTurnIn, ExpectedRevision, Error);
    ClientQuestResult(Accepted, bTurnIn, Error);
}
void AWarPlayerState::ClientQuestResult_Implementation(bool bAccepted, bool bTurnIn, const FString& Error)
{
    InventoryMessage = !bAccepted ? FText::FromString(Error) : bTurnIn
        ? NSLOCTEXT("AegisWar", "QuestCompleted", "Quest completed. Rewards received.")
        : NSLOCTEXT("AegisWar", "QuestAccepted", "Quest accepted.");
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

bool AWarPlayerState::AcceptCatalogQuestTrusted(FName QuestId, FName Zone, int32 ExpectedRevision, FString& Error)
{
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    FWarQuestDefinition Quest;
    if (!Content || !Content->GetQuest(QuestId, Quest, Error))
    { if (!Content) Error = TEXT("Quest catalog is unavailable."); return false; }
    return AcceptQuestTrusted(Quest, Zone, ExpectedRevision, Error);
}

bool AWarPlayerState::CompleteCatalogQuestTrusted(FName QuestId, FName Zone, int32 ExpectedRevision, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || Realm == EWarRealm::None || ExpectedRevision != Inventory.Revision)
    { Error = TEXT("Quest completion is unauthorized or character state changed."); return false; }
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    FWarQuestDefinition Quest;
    if (!Content || !Content->GetQuest(QuestId, Quest, Error))
    { if (!Content) Error = TEXT("Quest catalog is unavailable."); return false; }
    // Use the minimum affix only for capacity/precondition checks. Rejected turn-ins consume no random samples.
    TArray<FWarInventoryItem> Rewards;
    if (!WarQuests::ResolveRewards(Quest, [] { return 0.0; }, Rewards, Error)) return false;
    auto Progress = Inventory.Quests; FWarInventorySnapshot Preview;
    if (!WarQuests::TurnIn(Quest, QuestRealm(Realm), Zone, Rewards, Inventory, Progress, Preview, Error)) return false;
    if (!WarQuests::ResolveRewards(Quest, [] { return double(FMath::FRand()); }, Rewards, Error)) return false;
    return CompleteQuestTrusted(Quest, Zone, ExpectedRevision, Rewards, Error);
}

bool AWarPlayerState::RecordCatalogQuestKillTrusted(FName Zone, const FString& EnemyName, const FGuid& KillEvent, FString& Error)
{
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    if (!Content || !Content->IsContentReady()) { Error = TEXT("Quest catalog is unavailable."); return false; }
    TArray<FWarQuestDefinition> Active;
    for (const auto& Progress : Inventory.Quests)
    {
        if (Progress.Status != TEXT("active")) continue;
        FWarQuestDefinition Quest;
        if (!Content->GetQuest(Progress.Id, Quest, Error)) return false;
        Active.Add(Quest);
    }
    return RecordQuestKillTrusted(Active, Zone, EnemyName, KillEvent, Error);
}
