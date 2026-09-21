#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarContentSubsystem.h"
#include "WarCultivationRules.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCultivationTest, "AegisWar.Foundation.CultivationTransactions",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCultivationTest::RunTest(const FString& Parameters)
{
    FString Json, Error;
    if (!TestTrue(TEXT("Staged catalog exists"), FFileHelper::LoadFileToString(Json,
        *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/content.json"))))) return false;
    TSharedPtr<FJsonObject> Root;
    if (!TestTrue(TEXT("Catalog parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))) return false;
    const auto& Seeds = Root->GetObjectField(TEXT("crafting"))->GetArrayField(TEXT("seeds"));
    TestEqual(TEXT("Both source seeds covered"), Seeds.Num(), 2);
    for (const auto& Value : Seeds)
    {
        FWarCultivationSeed Seed;
        const FName Key(*Value->AsObject()->GetStringField(TEXT("seedKey")));
        if (!TestTrue(TEXT("Seed resolves"), UWarContentSubsystem::ParseCultivationSeed(Root, Key, Seed, Error))) continue;
        TestEqual(TEXT("Three plots retained"), Seed.SlotLimit, 3);
        TestEqual(TEXT("Source growth duration"), Seed.DurationMs, Key == TEXT("seed_mandrake") ? 30000 : 45000);
        TestEqual(TEXT("Source profession XP"), Seed.Xp, Key == TEXT("seed_mandrake") ? 8 : 10);
        for (bool Soil : {false, true})
        {
            FWarInventorySnapshot Inventory;
            FWarInventoryItem Item; Item.Key = Key; Item.Kind = TEXT("misc"); Item.Slot = 0; Item.Quantity = 4;
            Inventory.Items.Add(Item);
            if (Soil) { Item.Key = Seed.Additive; Item.Slot = 1; Inventory.Items.Add(Item); }
            const FGuid Id = FGuid::NewGuid();
            TestTrue(TEXT("Plant succeeds"), WarCultivation::Plant(Inventory, Seed, Soil, 1000, Id, Error));
            TestEqual(TEXT("Plant consumes one seed"), Inventory.Items[0].Quantity, 3);
            TestTrue(TEXT("No planting XP"), Inventory.Professions.IsEmpty());
            TestEqual(TEXT("Growth uses server timestamp"), Inventory.CultivationPlots[0].ReadyAtMs, int64(1000 + Seed.DurationMs));
            TestFalse(TEXT("Premature harvest rejected"), WarCultivation::Harvest(Inventory, Seed, Id, 999 + Seed.DurationMs, Error));
            TestEqual(TEXT("Rejected harvest preserves revision"), Inventory.Revision, 1);
            TestTrue(TEXT("Harvest at exact readiness"), WarCultivation::Harvest(Inventory, Seed, Id, 1000 + Seed.DurationMs, Error));
            TestTrue(TEXT("Harvest removes crop"), Inventory.CultivationPlots.IsEmpty());
            TestEqual(TEXT("Harvest XP once"), Inventory.Professions[0].Xp, Seed.Xp);
            int32 Quantity = 0;
            for (const auto& Reward : Inventory.Items) if (Reward.Key == Seed.Outputs[0].Key) Quantity += Reward.Quantity;
            TestEqual(TEXT("Soil bonus matches browser"), Quantity, Soil ? 3 : 2);
            TestFalse(TEXT("Repeated harvest cannot grant rewards"), WarCultivation::Harvest(Inventory, Seed, Id, 999999, Error));
            TestEqual(TEXT("Repeated harvest preserves revision"), Inventory.Revision, 2);
        }
        FWarInventorySnapshot Full;
        FWarInventoryItem Item; Item.Key = Key; Item.Kind = TEXT("misc"); Item.Slot = 0; Item.Quantity = 5; Full.Items.Add(Item);
        TestFalse(TEXT("Soil cannot be fabricated"), WarCultivation::Plant(Full, Seed, true, 0, FGuid::NewGuid(), Error));
        TestEqual(TEXT("Missing soil leaves seed untouched"), Full.Items[0].Quantity, 5);
        for (int32 Index = 0; Index < 3; ++Index)
            TestTrue(TEXT("Each plot usable"), WarCultivation::Plant(Full, Seed, false, 0, FGuid::NewGuid(), Error));
        TestFalse(TEXT("Fourth plot blocked"), WarCultivation::Plant(Full, Seed, false, 0, FGuid::NewGuid(), Error));
        for (int32 Index = 1; Index < 24; ++Index)
        { Item.Key = FName(*FString::Printf(TEXT("filler_%d"), Index)); Item.Slot = Index; Item.Quantity = 99; Full.Items.Add(Item); }
        const auto Id = Full.CultivationPlots[0].Id;
        TestFalse(TEXT("Full bag retains crop"), WarCultivation::Harvest(Full, Seed, Id, 999999, Error));
        TestEqual(TEXT("All plots remain after failure"), Full.CultivationPlots.Num(), 3);
        TestEqual(TEXT("Full bag leaves revision unchanged"), Full.Revision, 3);
        TestTrue(TEXT("Full bag grants no XP"), Full.Professions.IsEmpty());
        Full.Items.Pop();
        TestTrue(TEXT("Crop harvests after freeing space"), WarCultivation::Harvest(Full, Seed, Id, 999999, Error));
        TestFalse(TEXT("Timestamp overflow rejected"), WarCultivation::Plant(Full, Seed, false, MAX_int64, FGuid::NewGuid(), Error));
    }
    FWarCultivationSeed Invalid;
    TestFalse(TEXT("Invented seed rejected"), UWarContentSubsystem::ParseCultivationSeed(Root, TEXT("fake_seed"), Invalid, Error));
    return true;
}
#endif
