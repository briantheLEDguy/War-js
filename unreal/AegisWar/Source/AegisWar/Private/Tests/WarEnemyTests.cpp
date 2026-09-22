#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "WarEnemyRules.h"
#include "WarEnemyStateSubsystem.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarEnemyRulesTest, "AegisWar.Foundation.EnemySourceAndResidency",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarEnemyRulesTest::RunTest(const FString& Parameters)
{
    FString Json, Error; TSharedPtr<FJsonObject> Catalog;
    if (!TestTrue(TEXT("Staged source catalog exists"), FFileHelper::LoadFileToString(Json,
        *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/content.json"))))
        || !TestTrue(TEXT("Catalog parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Catalog))) return false;
    FWarEnemyDefinition Enemy;
    TestTrue(TEXT("Exact source raider resolves"), WarEnemies::Parse(Catalog, TEXT("sunmeadow_march"), TEXT("sunmeadow_march_west_raider_1"), Enemy, Error));
    TestEqual(TEXT("Source health"), Enemy.MaxHealth, 150.f);
    TestEqual(TEXT("Metres converted once"), Enemy.AggroRange, 1500.f);
    TestEqual(TEXT("Source speed"), Enemy.MoveSpeed, 325.f);
    TestEqual(TEXT("Exact visual identity"), Enemy.Profile, FName(TEXT("enemy_aegis_campaign_raider_raider")));
    TestFalse(TEXT("Cross-zone identity rejected"), WarEnemies::Parse(Catalog, TEXT("cinderfen_outskirts"), Enemy.Id, Enemy, Error));
    TestFalse(TEXT("Missing creature is not a raider"), WarEnemies::Parse(Catalog, TEXT("sunmeadow_march"), TEXT("sunmeadow_march_beast_1"), Enemy, Error));
    TestFalse(TEXT("Keep commander cannot use ordinary respawn behavior"), WarEnemies::Parse(Catalog, TEXT("sunmeadow_march"), TEXT("sunmeadow_march_aegis_keep_commander"), Enemy, Error));
    for (const auto* Capital : {TEXT("aegis_capital"), TEXT("riftspire_capital")})
    {
        for (int32 Index = 1; Index <= 3; ++Index)
        {
            FWarEnemyDefinition Dummy;
            const FName Id(*FString::Printf(TEXT("%s_training_dummy_%d"), Capital, Index));
            TestTrue(TEXT("Exact capital dummy resolves"), WarEnemies::Parse(Catalog, Capital, Id, Dummy, Error));
            TestTrue(TEXT("Dummy uses passive behavior"), Dummy.bTrainingDummy);
            TestTrue(TEXT("Dummy has no skeletal substitute"), Dummy.Profile.IsNone());
            TestEqual(TEXT("Dummy cannot aggro"), Dummy.AggroRange, 0.f);
            TestEqual(TEXT("Dummy cannot attack"), Dummy.AttackDamage, 0);
            TestEqual(TEXT("Dummy cannot move"), Dummy.MoveSpeed, 0.f);
            TestEqual(TEXT("Exact existing model"), Dummy.StaticModel, FString(FString(Capital) == TEXT("aegis_capital")
                ? TEXT("prop_training_dummy_t1.glb") : TEXT("prop_riftspire_training_dummy.glb")));
            TestEqual(TEXT("Source target health"), Dummy.MaxHealth, Index == 1 ? 60.f : Index == 2 ? 120.f : 90.f);
        }
    }
    const FName Zone(TEXT("sunmeadow_march"));
    TestTrue(TEXT("Live visible same-zone target within range"), WarEnemies::CanEngage(true, true, Zone, Zone, 90000, 0, 300));
    TestFalse(TEXT("Other zone cannot be hit"), WarEnemies::CanEngage(true, true, Zone, TEXT("cinderfen_outskirts"), 1, 0, 300));
    TestFalse(TEXT("Dead player cannot be hit"), WarEnemies::CanEngage(false, true, Zone, Zone, 1, 0, 300));
    TestFalse(TEXT("Invisible player cannot be hit"), WarEnemies::CanEngage(true, false, Zone, Zone, 1, 0, 300));
    TestFalse(TEXT("Vertical separation prevents hits through floors"), WarEnemies::CanEngage(true, true, Zone, Zone, 1, 300, 300));
    TestFalse(TEXT("Negative distance rejected"), WarEnemies::CanEngage(true, true, Zone, Zone, -1, 0, 300));
    auto* Cache = NewObject<UWarEnemyStateSubsystem>();
    auto& Life = Cache->FindOrCreate(Zone, Enemy.Id, 150);
    const FGuid Event = Life.Event; Life.Health = 0; Life.RespawnAt = 115;
    const auto& Reloaded = Cache->FindOrCreate(Zone, Enemy.Id, 150);
    TestEqual(TEXT("Reload retains dead health"), Reloaded.Health, 0.f);
    TestEqual(TEXT("Reload retains cooldown"), Reloaded.RespawnAt, 115.0);
    TestEqual(TEXT("Reload retains death receipt"), Reloaded.Event, Event);
    TestEqual(TEXT("Other enemy has independent health"), Cache->FindOrCreate(Zone, TEXT("other"), 160).Health, 160.f);
    // Invalid and duplicate source rows must not mutate an already parsed definition.
    auto Map = Catalog->GetArrayField(TEXT("maps")).FindByPredicate([Zone](const auto& Value) {
        return FName(*Value->AsObject()->GetStringField(TEXT("id"))) == Zone; });
    auto Definition = (*Map)->AsObject()->GetObjectField(TEXT("definition"));
    auto Enemies = Definition->GetArrayField(TEXT("enemies"));
    const auto Duplicate = Enemies[0];
    Enemies.Add(Duplicate); Definition->SetArrayField(TEXT("enemies"), Enemies);
    TestFalse(TEXT("Duplicate source row rejected"), WarEnemies::Parse(Catalog, Zone, FName(*Enemies[0]->AsObject()->GetStringField(TEXT("id"))), Enemy, Error));
    return true;
}
#endif
