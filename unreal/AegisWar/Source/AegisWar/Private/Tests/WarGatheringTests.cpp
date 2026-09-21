#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarContentSubsystem.h"
#include "WarGatheringRules.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarGatheringTest, "AegisWar.Foundation.ResourceGatheringTransactions",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarGatheringTest::RunTest(const FString& Parameters)
{
    FString Json, Error;
    if (!TestTrue(TEXT("Staged catalog exists"), FFileHelper::LoadFileToString(Json,
        *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/content.json"))))) return false;
    TSharedPtr<FJsonObject> Root;
    if (!TestTrue(TEXT("Catalog parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))) return false;
    int32 Count = 0;
    FWarResourceDefinition Example;
    for (const auto& Map : Root->GetArrayField(TEXT("maps")))
    {
        const FName Zone(*Map->AsObject()->GetStringField(TEXT("id")));
        const auto Definition = Map->AsObject()->GetObjectField(TEXT("definition"));
        const TArray<TSharedPtr<FJsonValue>>* Nodes = nullptr;
        if (!Definition->TryGetArrayField(TEXT("resourceNodes"), Nodes)) continue;
        for (const auto& Value : *Nodes)
        {
            const FName Id(*Value->AsObject()->GetStringField(TEXT("id")));
            FWarResourceDefinition Node;
            if (!TestTrue(Id.ToString(), UWarContentSubsystem::ParseResourceNode(Root, Zone, Id, Node, Error))) continue;
            ++Count; Example = Node;
            FWarInventorySnapshot Inventory; FRandomStream Random(123);
            TestTrue(TEXT("Known node yields loot"), WarGathering::Gather(Inventory, Node, 1000, Random, Error));
            TestFalse(TEXT("Guaranteed nonempty rewards"), Inventory.Items.IsEmpty());
            TestEqual(TEXT("Node awards source XP"), Inventory.Professions[0].Xp, Node.Xp);
            TestEqual(TEXT("Cooldown uses server timestamp"), Inventory.ResourceCooldowns[0].AvailableAtMs, 1000 + Node.CooldownMs);
            TestFalse(TEXT("Immediate repeat rejected"), WarGathering::Gather(Inventory, Node, 1000, Random, Error));
            TestEqual(TEXT("Repeat leaves revision unchanged"), Inventory.Revision, 1);
            TestFalse(TEXT("Still unavailable just before expiry"), WarGathering::IsAvailable(Inventory, Zone, Id, 999 + Node.CooldownMs));
            TestTrue(TEXT("Available at exact expiry"), WarGathering::Gather(Inventory, Node, 1000 + Node.CooldownMs, Random, Error));
            TestEqual(TEXT("Expired cooldown pruned before replacement"), Inventory.ResourceCooldowns.Num(), 1);
            TestEqual(TEXT("Second harvest awards XP once"), Inventory.Professions[0].Xp, Node.Xp * 2);
            FWarInventorySnapshot OtherCharacter;
            TestTrue(TEXT("Cooldown does not block another character"), WarGathering::IsAvailable(OtherCharacter, Zone, Id, 1000));
            TestTrue(TEXT("Same node name in another zone is independent"), WarGathering::IsAvailable(Inventory, TEXT("another_zone"), Id, 1000));
        }
    }
    TestEqual(TEXT("All 284 authored resource definitions execute"), Count, 284);
    if (Count == 0) return false;
    FWarInventorySnapshot Full;
    for (int32 Slot = 0; Slot < WarInventory::Capacity; ++Slot)
    { FWarInventoryItem Item; Item.Key = FName(*FString::Printf(TEXT("filler_%d"), Slot)); Item.Kind = TEXT("misc"); Item.Quantity = 99; Item.Slot = Slot; Full.Items.Add(Item); }
    FRandomStream Random(123);
    TestFalse(TEXT("Full bag rejects gather atomically"), WarGathering::Gather(Full, Example, 1000, Random, Error));
    TestEqual(TEXT("Full bag preserves revision"), Full.Revision, 0);
    TestTrue(TEXT("Full bag grants no XP"), Full.Professions.IsEmpty());
    TestTrue(TEXT("Full bag starts no cooldown"), Full.ResourceCooldowns.IsEmpty());
    TestTrue(TEXT("Gather does not defer overflow"), Full.PendingRewards.IsEmpty());
    auto Guaranteed = Example;
    for (auto& Entry : Guaranteed.Loot) Entry.Chance = 0;
    FWarInventorySnapshot Fallback;
    TestTrue(TEXT("All missed rolls still grant the browser fallback"), WarGathering::Gather(Fallback, Guaranteed, 1000, Random, Error));
    TestEqual(TEXT("Fallback identity"), Fallback.Items[0].Key, Guaranteed.Loot[0].Item.Key);
    TestEqual(TEXT("Fallback uses base quantity"), Fallback.Items[0].Quantity, Guaranteed.Loot[0].Item.Quantity);
    FWarInventorySnapshot Invalid;
    TestFalse(TEXT("Timestamp overflow rejected"), WarGathering::Gather(Invalid, Example, MAX_int64, Random, Error));
    Guaranteed.Loot[0].Chance = 2;
    TestFalse(TEXT("Invalid probabilities rejected"), WarGathering::Gather(Invalid, Guaranteed, 0, Random, Error));
    TestFalse(TEXT("Fabricated node rejected"), UWarContentSubsystem::ParseResourceNode(Root, Example.ZoneId, TEXT("fabricated"), Example, Error));
    return true;
}
#endif
