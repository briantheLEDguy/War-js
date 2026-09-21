#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarQuestRules.h"
#include "WarContentSubsystem.h"
#include "WarPlayerState.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarQuestTest, "AegisWar.Foundation.ExpeditionQuestParity",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarQuestTest::RunTest(const FString& Parameters)
{
    FString Json, Error;
    TSharedPtr<FJsonObject> Catalog, Fixtures;
    if (!FFileHelper::LoadFileToString(Json, *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/content.json")))
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Catalog)) return false;
    if (!FFileHelper::LoadFileToString(Json, *FPaths::Combine(FPaths::ProjectDir(), TEXT("../../migration/fixtures/quests.json")))
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Fixtures)) return false;
    TMap<FName, FWarQuestDefinition> Definitions;
    TMap<FName, TArray<FWarInventoryItem>> Rewards;
    auto Name = [](const TSharedPtr<FJsonObject>& Object, const TCHAR* Key) {
        FString Value; Object->TryGetStringField(Key, Value); return FName(*Value); };
    if (!TestTrue(TEXT("Runtime quest catalog validates"), UWarContentSubsystem::ParseQuestCatalog(Catalog, Definitions, Error))) return false;
    for (const auto& Pair : Definitions)
    {
        TArray<FWarInventoryItem> Resolved;
        if (!TestTrue(TEXT("Runtime reward resolution"), WarQuests::ResolveRewards(Pair.Value,
            [&] { return Fixtures->GetNumberField(TEXT("randomUnit")); }, Resolved, Error))) return false;
        Rewards.Add(Pair.Key, MoveTemp(Resolved));
    }
    TestEqual(TEXT("All eight source quests"), Definitions.Num(), 8);
    for (const auto& Value : Catalog->GetArrayField(TEXT("quests")))
    {
        const auto Row = Value->AsObject();
        const auto& Quest = Definitions.FindChecked(Name(Row, TEXT("id")));
        for (int32 Index = 0; Index < Quest.Objectives.Num(); ++Index)
            TestEqual(TEXT("Objective description preserved for quest log"), Quest.Objectives[Index].Description,
                Row->GetArrayField(TEXT("objectives"))[Index]->AsObject()->GetStringField(TEXT("description")));
    }
    FString CatalogJson;
    FJsonSerializer::Serialize(Catalog.ToSharedRef(), TJsonWriterFactory<>::Create(&CatalogJson));
    const auto Reject = [&](const TCHAR* Label, TFunction<void(TSharedPtr<FJsonObject>)> Mutate) {
        TSharedPtr<FJsonObject> Broken;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(CatalogJson), Broken);
        Mutate(Broken); auto Preserved = Definitions;
        TestFalse(Label, UWarContentSubsystem::ParseQuestCatalog(Broken, Preserved, Error));
        TestEqual(TEXT("Rejected catalog leaves prior output intact"), Preserved.Num(), 8);
    };
    Reject(TEXT("Duplicate quest rejected"), [](auto Root) {
        auto Rows = Root->GetArrayField(TEXT("quests")); const auto Duplicate = Rows[0]; Rows.Add(Duplicate); Root->SetArrayField(TEXT("quests"), Rows); });
    Reject(TEXT("Unknown reward rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[0]->AsObject()->GetObjectField(TEXT("reward"))->GetArrayField(TEXT("items"))[0]->AsObject()->SetStringField(TEXT("key"), TEXT("missing")); });
    Reject(TEXT("Unknown zone rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[0]->AsObject()->SetStringField(TEXT("giverZoneId"), TEXT("missing")); });
    Reject(TEXT("Fractional objective rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[0]->AsObject()->GetArrayField(TEXT("objectives"))[0]->AsObject()->SetNumberField(TEXT("required"), 1.5); });
    Reject(TEXT("Missing objective description rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[0]->AsObject()->GetArrayField(TEXT("objectives"))[0]->AsObject()->RemoveField(TEXT("description")); });
    Reject(TEXT("Duplicate objective rejected"), [](auto Root) {
        auto Quest = Root->GetArrayField(TEXT("quests"))[0]->AsObject(); auto Rows = Quest->GetArrayField(TEXT("objectives"));
        const auto Duplicate = Rows[0]; Rows.Add(Duplicate); Quest->SetArrayField(TEXT("objectives"), Rows); });
    Reject(TEXT("Missing prerequisite rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[0]->AsObject()->SetStringField(TEXT("prereqQuestId"), TEXT("missing")); });
    Reject(TEXT("Prerequisite cycle rejected"), [](auto Root) {
        auto Rows = Root->GetArrayField(TEXT("quests")); Rows[0]->AsObject()->SetStringField(TEXT("prereqQuestId"), Rows[1]->AsObject()->GetStringField(TEXT("id"))); });
    Reject(TEXT("Cross-realm prerequisite rejected"), [](auto Root) {
        auto Rows = Root->GetArrayField(TEXT("quests")); Rows[0]->AsObject()->SetStringField(TEXT("prereqQuestId"), Rows[4]->AsObject()->GetStringField(TEXT("id"))); });
    Reject(TEXT("Malformed optional reward array rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[0]->AsObject()->GetObjectField(TEXT("reward"))->SetStringField(TEXT("items"), TEXT("invalid")); });
    Reject(TEXT("Reversed affix range rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[3]->AsObject()->GetObjectField(TEXT("reward"))->GetArrayField(TEXT("items"))[0]->AsObject()->GetObjectField(TEXT("strengthRoll"))->SetNumberField(TEXT("min"), 99); });
    Reject(TEXT("Null optional field rejected"), [](auto Root) {
        Root->GetArrayField(TEXT("quests"))[0]->AsObject()->SetField(TEXT("giverZoneId"), MakeShared<FJsonValueNull>()); });
    {
        const auto& Quest = Definitions.FindChecked(TEXT("dawnline-04-keep"));
        TArray<FWarInventoryItem> Items;
        TestTrue(TEXT("Lowest affix roll"), WarQuests::ResolveRewards(Quest, [] { return 0.0; }, Items, Error));
        TestEqual(TEXT("Affix minimum"), Items[0].StrengthBonus, 3);
        TestTrue(TEXT("Highest affix roll"), WarQuests::ResolveRewards(Quest, [] { return 0.999999; }, Items, Error));
        TestEqual(TEXT("Affix maximum"), Items[0].StrengthBonus, 7);
        TestFalse(TEXT("Out-of-range random input rejected"), WarQuests::ResolveRewards(Quest, [] { return 1.0; }, Items, Error));
        TestEqual(TEXT("Failed roll leaves output intact"), Items[0].StrengthBonus, 7);
    }

    for (const auto& Case : Fixtures->GetArrayField(TEXT("cases")))
    {
        const auto Scenario = Case->AsObject(); const FName Realm = Name(Scenario, TEXT("realm"));
        FWarInventorySnapshot Inventory; TArray<FWarQuestProgress> Progress;
        TArray<FWarInventoryItem> SavedItems;
        for (const auto& Entry : Scenario->GetArrayField(TEXT("steps")))
        {
            const auto Step = Entry->AsObject(); FString Id, Action;
            const FString Label = Step->GetStringField(TEXT("action"));
            if (!Label.Split(TEXT(":"), &Id, &Action)) Action = Label;
            const FWarQuestDefinition* Quest = Definitions.Find(FName(*Id));
            if (Action == TEXT("reject_other_realm") || Action == TEXT("reject_missing_prerequisite"))
            {
                for (const auto& Pair : Definitions)
                    if ((Action == TEXT("reject_other_realm") && Pair.Value.Realm != Realm && Pair.Value.Prerequisite.IsNone())
                        || (Action == TEXT("reject_missing_prerequisite") && Pair.Value.Realm == Realm && Pair.Key.ToString().Contains(TEXT("02-guards"))))
                        TestFalse(Label, WarQuests::Accept(Pair.Value, Realm, Pair.Value.GiverZoneId, 1, Progress, Error));
            }
            else if (!TestNotNull(Label, Quest)) return false;
            else if (Action == TEXT("accept") || Action == TEXT("duplicate_accept") || Action == TEXT("reject_wrong_giver_zone"))
                TestEqual(Label, WarQuests::Accept(*Quest, Realm, Action == TEXT("reject_wrong_giver_zone") ? FName(TEXT("zone1")) : Quest->GiverZoneId,
                    Inventory.CharacterProgression.Level, Progress, Error), Action == TEXT("accept"));
            else if (Action == TEXT("reject_wrong_kill_zone"))
                TestFalse(Label, WarQuests::Kill(*Quest, Realm, TEXT("zone1"), Quest->Objectives[0].KillTarget, Progress));
            else if (Action == TEXT("kills_complete_and_clamped"))
            {
                for (const auto& Objective : Quest->Objectives)
                    for (int32 Kill = 0; Kill <= Objective.Required; ++Kill)
                        WarQuests::Kill(*Quest, Realm, Objective.ZoneId, Objective.KillTarget, Progress);
            }
            else
            {
                if (Action == TEXT("reject_full_bag"))
                {
                    SavedItems = Inventory.Items; Inventory.Items.Empty();
                    for (int32 Slot = 0; Slot < 24; ++Slot)
                    {
                        FWarInventoryItem Item; Item.Key = TEXT("jewel_amulet_bloodglass"); Item.Kind = TEXT("armor");
                        Item.EquipSlot = TEXT("neck"); Item.Slot = Slot; Inventory.Items.Add(Item);
                    }
                }
                if (Action == TEXT("complete")) Inventory.Items = SavedItems;
                FWarInventorySnapshot Next;
                const bool Accepted = WarQuests::TurnIn(*Quest, Realm, Action == TEXT("reject_wrong_turnin_zone") ? FName(TEXT("zone1")) : Quest->TurninZoneId,
                    Rewards.FindChecked(Quest->Id), Inventory, Progress, Next, Error);
                TestEqual(Label, Accepted, Action == TEXT("complete"));
                if (Accepted) Inventory = Next;
            }
            const auto Expected = Step->GetObjectField(TEXT("character"));
            TestEqual(Label + TEXT(" level"), Inventory.CharacterProgression.Level, Expected->GetIntegerField(TEXT("level")));
            TestEqual(Label + TEXT(" xp"), Inventory.CharacterProgression.Xp, int64(Expected->GetIntegerField(TEXT("xp"))));
            TestEqual(Label + TEXT(" gold"), Inventory.CharacterProgression.Gold, int64(Expected->GetIntegerField(TEXT("gold"))));
            TestEqual(Label + TEXT(" strength"), Inventory.CharacterProgression.BaseStrength, Expected->GetIntegerField(TEXT("strength")));
            TestEqual(Label + TEXT(" health cap"), Inventory.CharacterProgression.MaxHealth, Expected->GetIntegerField(TEXT("maxHealth")));
            TestEqual(Label + TEXT(" mana cap"), Inventory.CharacterProgression.MaxMana, Expected->GetIntegerField(TEXT("maxMana")));
            TestEqual(Label + TEXT(" quest count"), Progress.Num(), Step->GetArrayField(TEXT("quests")).Num());
            for (const auto& ExpectedQuest : Step->GetArrayField(TEXT("quests")))
            {
                const auto Row = ExpectedQuest->AsObject();
                const auto* Actual = Progress.FindByPredicate([&](const auto& Q) { return Q.Id == Name(Row, TEXT("questId")); });
                if (!TestNotNull(Label, Actual)) continue;
                TestEqual(Label + TEXT(" status"), Actual->Status, Name(Row, TEXT("status")));
                for (const auto& Counter : Row->GetObjectField(TEXT("counters"))->Values)
                    TestEqual(Label + Counter.Key, Actual->GetCount(FName(*Counter.Key)), int32(Counter.Value->AsNumber()));
            }
            TestEqual(Label + TEXT(" item count"), Inventory.Items.Num(), Step->GetArrayField(TEXT("inventory")).Num());
            for (const auto& ExpectedItem : Step->GetArrayField(TEXT("inventory")))
            {
                const auto Row = ExpectedItem->AsObject(); const int32 Slot = Row->GetIntegerField(TEXT("slot"));
                const auto* Actual = Inventory.Items.FindByPredicate([&](const auto& Item) { return Item.Slot == Slot; });
                if (!TestNotNull(Label, Actual)) continue;
                TestEqual(Label + TEXT(" item key"), Actual->Key, Name(Row, TEXT("key")));
                TestEqual(Label + TEXT(" quantity"), Actual->Quantity, Row->GetIntegerField(TEXT("qty")));
                const TSharedPtr<FJsonObject>* Affix = nullptr;
                const bool HasAffix = Row->TryGetObjectField(TEXT("affix"), Affix);
                TestEqual(Label + TEXT(" affix present"), Actual->bHasAffix, HasAffix);
                if (HasAffix) TestEqual(Label + TEXT(" strength roll"), Actual->StrengthBonus, (*Affix)->GetIntegerField(TEXT("strengthBonus")));
            }
        }
    }
    {
        auto Quest = Definitions.FindChecked(TEXT("dawnline-01-scouting"));
        TArray<FWarQuestProgress> Progress;
        Quest.MinLevel = 2;
        TestFalse(TEXT("Minimum level is enforced"), WarQuests::Accept(Quest, TEXT("aegis"), Quest.GiverZoneId, 1, Progress, Error));
        Quest.MinLevel = 1;
        TestTrue(TEXT("Boundary level accepted"), WarQuests::Accept(Quest, TEXT("aegis"), Quest.GiverZoneId, 1, Progress, Error));
        Progress[0].Status = TEXT("ready_to_turn_in");
        FWarInventorySnapshot Before, After;
        TestFalse(TEXT("Forged ready status without counters cannot pay"), WarQuests::TurnIn(Quest, TEXT("aegis"), Quest.TurninZoneId, Rewards.FindChecked(Quest.Id), Before, Progress, After, Error));
        Progress[0].SetCount(Quest.Objectives[0].Id, Quest.Objectives[0].Required);
        Before.CharacterProgression.Gold = MAX_int64;
        TestFalse(TEXT("Progression overflow rolls back quest completion"), WarQuests::TurnIn(Quest, TEXT("aegis"), Quest.TurninZoneId, Rewards.FindChecked(Quest.Id), Before, Progress, After, Error));
        TestEqual(TEXT("Overflow keeps ready quest"), Progress[0].Status, FName(TEXT("ready_to_turn_in")));
        TestTrue(TEXT("Overflow keeps output empty"), After.Items.IsEmpty());
    }
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Quest authority world"), World)) return false;
    auto* State = World->SpawnActor<AWarPlayerState>();
    if (!TestNotNull(TEXT("Quest authority owner"), State)) { World->DestroyWorld(false); return false; }
    State->SetDevelopmentRealm(EWarRealm::Aegis);
    const auto& Quest = Definitions.FindChecked(TEXT("dawnline-01-scouting"));
    const FGuid OldKill = FGuid::NewGuid();
    TestTrue(TEXT("Unmatched kill receipt recorded"), State->RecordQuestKillTrusted({Quest}, Quest.Objectives[0].ZoneId, Quest.Objectives[0].KillTarget, OldKill, Error));
    TestTrue(TEXT("Trusted quest acceptance"), State->AcceptQuestTrusted(Quest, Quest.GiverZoneId, 0, Error));
    TestFalse(TEXT("Old kill cannot replay after acceptance"), State->RecordQuestKillTrusted({Quest}, Quest.Objectives[0].ZoneId, Quest.Objectives[0].KillTarget, OldKill, Error));
    TestFalse(TEXT("Stale quest command rejected"), State->AcceptQuestTrusted(Quest, Quest.GiverZoneId, 0, Error));
    TestEqual(TEXT("Acceptance revision"), State->GetInventory().Revision, 1);
    const FGuid Kill = FGuid::NewGuid();
    TestFalse(TEXT("Duplicate definitions do not double-count or partially commit"), State->RecordQuestKillTrusted({Quest, Quest}, Quest.Objectives[0].ZoneId, Quest.Objectives[0].KillTarget, Kill, Error));
    TestEqual(TEXT("Bad catalog leaves counter zero"), State->GetInventory().Quests[0].GetCount(Quest.Objectives[0].Id), 0);
    for (int32 Count = 0; Count < 4; ++Count)
        TestTrue(TEXT("Unique kill advances quest"), State->RecordQuestKillTrusted({Quest}, Quest.Objectives[0].ZoneId, Quest.Objectives[0].KillTarget, FGuid::NewGuid(), Error));
    TestEqual(TEXT("Ready revision"), State->GetInventory().Revision, 5);
    TestTrue(TEXT("Quest completion commits snapshot"), State->CompleteQuestTrusted(Quest, Quest.TurninZoneId, 5, Rewards.FindChecked(Quest.Id), Error));
    TestEqual(TEXT("Completion revision"), State->GetInventory().Revision, 6);
    TestEqual(TEXT("Quest status in owner snapshot"), State->GetInventory().Quests[0].Status, FName(TEXT("completed")));
    TestEqual(TEXT("Gold settled"), State->GetInventory().CharacterProgression.Gold, int64(8));
    TestFalse(TEXT("Fresh-revision retry cannot replay completed reward"), State->CompleteQuestTrusted(Quest, Quest.TurninZoneId, 6, Rewards.FindChecked(Quest.Id), Error));
    TestEqual(TEXT("Retry retains gold"), State->GetInventory().CharacterProgression.Gold, int64(8));
    World->DestroyWorld(false);
    return true;
}
#endif
