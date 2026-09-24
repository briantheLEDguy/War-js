#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarProgressionRules.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Misc/ScopeExit.h"

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
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* State = World->SpawnActor<AWarPlayerState>();
    if (!TestNotNull(TEXT("Reward owner"), State)) return false;
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
    State->GetAbilitySystemComponent()->InitAbilityActorInfo(State, State);
    const auto Snapshot = State->GetInventory();
    TestTrue(TEXT("GM can set level 45"), State->SetGmLevelTrusted(45, Error));
    const auto& Leveled = State->GetInventory();
    TestEqual(TEXT("GM level applied"), Leveled.CharacterProgression.Level, 45);
    TestEqual(TEXT("GM XP reset"), Leveled.CharacterProgression.Xp, int64(0));
    TestEqual(TEXT("GM preserves gold"), Leveled.CharacterProgression.Gold, int64(25));
    TestEqual(TEXT("GM retains equipped strength bonus"), State->GetEffectiveStrength(), int64(105));
    TestEqual(TEXT("GM retains equipment"), Leveled.Equipment.Num(), Snapshot.Equipment.Num());
    TestEqual(TEXT("GM retains bag"), Leveled.Items.Num(), Snapshot.Items.Num());
    TestEqual(TEXT("GM retains pending rewards"), Leveled.PendingRewards.Num(), Snapshot.PendingRewards.Num());
    TestEqual(TEXT("GM increments inventory revision"), Leveled.Revision, Snapshot.Revision + 1);
    TestEqual(TEXT("GM updates GAS max health"), State->GetAttributes()->GetMaxHealth(), 980.f);
    TestEqual(TEXT("GM restores GAS health"), State->GetAttributes()->GetHealth(), 980.f);
    TestEqual(TEXT("GM updates GAS max mana"), State->GetAttributes()->GetMaxMana(), 540.f);
    TestEqual(TEXT("GM restores GAS mana"), State->GetAttributes()->GetMana(), 540.f);
    for (int32 Invalid : {MIN_int32, 0, 46, MAX_int32})
        TestFalse(TEXT("GM rejects out-of-range levels"), State->SetGmLevelTrusted(Invalid, Error));
    TestEqual(TEXT("Rejected GM change preserves revision"), Leveled.Revision, Snapshot.Revision + 1);
    TestEqual(TEXT("Rejected GM change preserves level"), Leveled.CharacterProgression.Level, 45);
    TestTrue(TEXT("GM can return to level one"), State->SetGmLevelTrusted(1, Error));
    TestEqual(TEXT("Lowered health returns to baseline"), State->GetAttributes()->GetHealth(), 100.f);
    TestEqual(TEXT("Lowered mana returns to baseline"), State->GetAttributes()->GetMana(), 100.f);
    TestEqual(TEXT("Lowered strength retains gear"), State->GetEffectiveStrength(), int64(17));
    TestTrue(TEXT("Setting same level does not compound growth"), State->SetGmLevelTrusted(1, Error));
    TestEqual(TEXT("Same-level strength unchanged"), State->GetEffectiveStrength(), int64(17));
    Before = {}; Before.MaxHealth += 50; Before.BaseStrength += 3; Before.Xp = 99;
    TestTrue(TEXT("Non-level stat offsets retained on raising"), WarProgression::SetGmLevel(Before, 45, After, Error));
    TestEqual(TEXT("Health offset retained"), After.MaxHealth, 1030);
    TestTrue(TEXT("Offsets retained on lowering"), WarProgression::SetGmLevel(After, 1, Before, Error));
    TestEqual(TEXT("Strength offset round trip"), Before.BaseStrength, 13);
    Before.MaxHealth = MAX_int32;
    TestFalse(TEXT("GM overflow rejected"), WarProgression::SetGmLevel(Before, 45, After, Error));
    Before = {}; Before.Level = 45;
    TestFalse(TEXT("GM cannot lower to invalid stats"), WarProgression::SetGmLevel(Before, 1, After, Error));
    return true;
}
#endif
