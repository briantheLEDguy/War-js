#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarProgressionRules.h"
#include "WarPlayerState.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarProgressionTest, "AegisWar.Foundation.CharacterProgressionParity",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarProgressionTest::RunTest(const FString& Parameters)
{
    FString Json, Error;
    if (!TestTrue(TEXT("Browser progression fixtures exist"), FFileHelper::LoadFileToString(Json,
        *FPaths::Combine(FPaths::ProjectDir(), TEXT("../../migration/fixtures/progression.json"))))) return false;
    TSharedPtr<FJsonObject> Root;
    if (!TestTrue(TEXT("Fixtures parse"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))) return false;
    const auto& Cases = Root->GetArrayField(TEXT("cases"));
    TestEqual(TEXT("All nine source boundary/multilevel cases run"), Cases.Num(), 9);
    for (const auto& Value : Cases)
    {
        const auto Row = Value->AsObject(); const auto Input = Row->GetObjectField(TEXT("input"));
        const auto Expected = Row->GetObjectField(TEXT("expected"));
        FWarCharacterProgression Before, After;
        Before.Level = Input->GetIntegerField(TEXT("level")); Before.Xp = Input->GetIntegerField(TEXT("xp"));
        Before.Gold = Input->GetIntegerField(TEXT("gold")); Before.BaseStrength = Input->GetIntegerField(TEXT("strength"));
        Before.MaxHealth = Input->GetIntegerField(TEXT("maxHealth")); Before.MaxMana = Input->GetIntegerField(TEXT("maxMana"));
        if (!TestTrue(Row->GetStringField(TEXT("name")), WarProgression::Award(Before,
            Row->GetIntegerField(TEXT("xpReward")), Row->GetIntegerField(TEXT("goldReward")), After, Error))) continue;
        TestEqual(TEXT("Level"), After.Level, Expected->GetIntegerField(TEXT("level")));
        TestEqual(TEXT("Remaining XP"), After.Xp, int64(Expected->GetIntegerField(TEXT("xp"))));
        TestEqual(TEXT("Gold"), After.Gold, int64(Expected->GetIntegerField(TEXT("gold"))));
        TestEqual(TEXT("Base strength"), After.BaseStrength, Expected->GetIntegerField(TEXT("strength")));
        TestEqual(TEXT("Max health"), After.MaxHealth, Expected->GetIntegerField(TEXT("maxHealth")));
        TestEqual(TEXT("Max mana"), After.MaxMana, Expected->GetIntegerField(TEXT("maxMana")));
    }
    FWarCharacterProgression Before, After;
    TestFalse(TEXT("Negative XP rejected"), WarProgression::Award(Before, -1, 0, After, Error));
    Before.Gold = MAX_int64;
    TestFalse(TEXT("Gold overflow rejected"), WarProgression::Award(Before, 0, 1, After, Error));
    Before = {}; Before.MaxHealth = MAX_int32;
    TestFalse(TEXT("Growth overflow rejected atomically"), WarProgression::Award(Before, 250, 0, After, Error));
    TestEqual(TEXT("Failed growth leaves output untouched"), After.Level, 1);
    Before = {};
    TestTrue(TEXT("Largest bounded reward terminates"), WarProgression::Award(Before, MAX_int32, 0, After, Error));
    TestTrue(TEXT("Result remains normalized"), After.Xp < WarProgression::XpForLevel(After.Level));
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Reward test world"), World)) return false;
    auto* State = World->SpawnActor<AWarPlayerState>();
    if (!TestNotNull(TEXT("Reward owner"), State)) { World->DestroyWorld(false); return false; }
    FWarInventoryItem Gear; Gear.Key = TEXT("test_gear"); Gear.Kind = TEXT("weapon"); Gear.EquipSlot = TEXT("mainHand");
    Gear.Quantity = 25; Gear.bHasAffix = true; Gear.StrengthBonus = 7;
    const FGuid Id = FGuid::NewGuid();
    TestTrue(TEXT("XP/gold and deferred gear commit together"), State->GrantCharacterRewards(Id, 650, 25, {Gear}, Error));
    TestEqual(TEXT("Two levels gained"), State->GetInventory().CharacterProgression.Level, 3);
    TestEqual(TEXT("Gold granted once"), State->GetInventory().CharacterProgression.Gold, int64(25));
    TestEqual(TEXT("Full bag retains overflow"), State->GetInventory().PendingRewards.Num(), 1);
    TestFalse(TEXT("Retry cannot replay progression"), State->GrantCharacterRewards(Id, 650, 25, {Gear}, Error));
    TestEqual(TEXT("Retry preserves level"), State->GetInventory().CharacterProgression.Level, 3);
    TestEqual(TEXT("Retry preserves revision"), State->GetInventory().Revision, 1);
    TestTrue(TEXT("Gear equips after progression"), State->ChangeEquipment(1, 0, true, Error));
    TestEqual(TEXT("Equipment adds without changing base growth"), State->GetEffectiveStrength(), int64(21));
    Gear.Quantity = 0;
    TestFalse(TEXT("Bad item rolls back XP and gold"), State->GrantCharacterRewards(FGuid::NewGuid(), 550, 30, {Gear}, Error));
    TestEqual(TEXT("Failed reward retains level"), State->GetInventory().CharacterProgression.Level, 3);
    TestEqual(TEXT("Failed reward retains gold"), State->GetInventory().CharacterProgression.Gold, int64(25));
    World->DestroyWorld(false);
    return true;
}
#endif
