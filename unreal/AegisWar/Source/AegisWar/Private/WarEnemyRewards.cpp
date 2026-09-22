#include "WarPlayerState.h"
#include "WarContentSubsystem.h"
#include "WarEnemyRules.h"
#include "Engine/GameInstance.h"

bool AWarPlayerState::AwardEnemyKillTrusted(FName Zone, FName EnemyId, const FGuid& KillEvent,
    const TArray<FWarInventoryItem>& Loot, FString& Error)
{
    Error = TEXT("Enemy reward is unauthorized, duplicated or character state is unavailable.");
    if (!HasAuthority() || Realm == EWarRealm::None || CurrentZone != Zone || !KillEvent.IsValid()
        || RewardReceipts.Contains(KillEvent) || QuestKillReceipts.Contains(KillEvent)
        || RewardReceipts.Num() >= 65536 || QuestKillReceipts.Num() >= 65536 || Inventory.Revision == MAX_int32) return false;
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    FWarEnemyDefinition Enemy;
    if (!Content || !Content->IsContentReady()
        || !WarEnemies::Parse(Content->GetInterfaceCatalogSource(), Zone, EnemyId, Enemy, Error)
        || Enemy.bTrainingDummy) return false;
    auto Next = Inventory;
    if (!WarProgression::Award(Inventory.CharacterProgression, 20 + Enemy.Level * 10, 0, Next.CharacterProgression, Error)) return false;
    TArray<FWarInventoryItem> Pending;
    if (!WarInventory::PlaceRewards(Inventory.Items, Loot, Next.Items, Pending, Error)) return false;
    Next.PendingRewards.Append(Pending);
    const FName PlayerRealm = Realm == EWarRealm::Aegis ? FName(TEXT("aegis")) : FName(TEXT("riftbound"));
    for (const auto& Progress : Inventory.Quests)
    {
        if (Progress.Status != TEXT("active")) continue;
        FWarQuestDefinition Quest;
        if (!Content->GetQuest(Progress.Id, Quest, Error)) return false;
        WarQuests::Kill(Quest, PlayerRealm, Zone, Enemy.Name, Next.Quests);
    }
    const bool bLeveled = Next.CharacterProgression.Level > Inventory.CharacterProgression.Level;
    ++Next.Revision;
    // XP, deferred loot and quest counters share one commit and one death receipt.
    Inventory = MoveTemp(Next); RewardReceipts.Add(KillEvent); QuestKillReceipts.Add(KillEvent);
    if (bLeveled) ApplyProgressionVitals(true);
    ForceNetUpdate(); Error.Reset(); return true;
}
