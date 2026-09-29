#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "WarEnemyRules.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarImportedPopulationTest, "AegisWar.Foundation.ImportedPopulation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarImportedPopulationTest::RunTest(const FString& Parameters)
{
    FString Json, Error; TSharedPtr<FJsonObject> Catalog;
    // The exported source is sufficient to check parsing; this does not admit staged visuals.
    const FString Source = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../../artifacts/unreal/content.json"));
    if (!TestTrue(TEXT("Current exported catalog exists"), FFileHelper::LoadFileToString(Json, *Source))
        || !TestTrue(TEXT("Catalog parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Catalog))) return false;
    for (const auto& Pair : {TPair<FString,int32>(TEXT("brightfen_approach"),3),TPair<FString,int32>(TEXT("ashen_steppe"),4)})
    {
        const FString Camp = Pair.Key == TEXT("brightfen_approach") ? TEXT("deserter_camp") : TEXT("cultist_camp");
        for (int32 Index=1;Index<=Pair.Value;++Index)
        {
            FWarEnemyDefinition Enemy;
            const FName Id(*(Pair.Key+TEXT("_import_")+Camp+TEXT("_")+FString::FromInt(Index)));
            TestTrue(TEXT("New hostile camp member has supported authoritative behavior"), WarEnemies::Parse(Catalog,FName(*Pair.Key),Id,Enemy,Error));
            TestEqual(TEXT("Local level-three tuning"),Enemy.Level,3);
            TestEqual(TEXT("Ordinary melee health"),Enemy.MaxHealth,150.f);
            TestFalse(TEXT("No training dummy substitution"),Enemy.bTrainingDummy);
            TestTrue(TEXT("Exact imported profile"),Enemy.Profile.ToString().StartsWith(TEXT("npc_import_")));
        }
    }
    FWarEnemyDefinition Friendly;
    TestFalse(TEXT("Friendly supply sentry cannot become an enemy"),WarEnemies::Parse(Catalog,TEXT("sunmeadow_march"),
        TEXT("sunmeadow_march_import_supply_outpost_1"),Friendly,Error));
    TestFalse(TEXT("Friendly work crew cannot become an enemy"),WarEnemies::Parse(Catalog,TEXT("cinderfen_outskirts"),
        TEXT("cinderfen_outskirts_import_work_crew_1"),Friendly,Error));
    return true;
}
#endif
