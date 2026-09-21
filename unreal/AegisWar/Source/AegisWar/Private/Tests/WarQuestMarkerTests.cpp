#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarContentSubsystem.h"
#include "WarQuestMarkerRules.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarQuestMarkerTest, "AegisWar.Foundation.QuestMarkerVisibility",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarQuestMarkerTest::RunTest(const FString& Parameters)
{
    FString Json, Error; TSharedPtr<FJsonObject> Catalog;
    TMap<FName, FWarQuestDefinition> ById;
    if (!FFileHelper::LoadFileToString(Json, *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/content.json")))
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Catalog)
        || !UWarContentSubsystem::ParseQuestCatalog(Catalog, ById, Error)) return false;
    TArray<FWarQuestDefinition> Quests; ById.GenerateValueArray(Quests);
    for (const FName Id : {FName(TEXT("dawnline-01-scouting")), FName(TEXT("cinderfen-01-scouting"))})
    {
        const auto& Quest = ById.FindChecked(Id);
        TArray<FWarQuestProgress> Progress;
        const auto At = [&](FName Zone, FName Npc, int32 Level = 1) {
            return WarQuestMarkers::Resolve(Quests, Progress, Quest.Realm, Zone, Npc, Level); };
        TestTrue(TEXT("Fresh capital offer"), At(Quest.GiverZoneId, Quest.GiverNpcId) == EWarQuestMarker::Offer);
        TestTrue(TEXT("Field prerequisite not yet complete"), At(Quest.TurninZoneId, Quest.TurninNpcId) == EWarQuestMarker::None);
        TestTrue(TEXT("Level requirement retained"), At(Quest.GiverZoneId, Quest.GiverNpcId, 0) == EWarQuestMarker::None);
        TestTrue(TEXT("Wrong zone has no offer"), At(TEXT("zone1"), Quest.GiverNpcId) == EWarQuestMarker::None);
        TestTrue(TEXT("Unknown NPC has no marker"), At(Quest.GiverZoneId, TEXT("unknown")) == EWarQuestMarker::None);
        TestTrue(TEXT("Unknown realm has no marker"), WarQuestMarkers::Resolve(Quests, Progress, NAME_None,
            Quest.GiverZoneId, Quest.GiverNpcId, 1) == EWarQuestMarker::None);
        TestTrue(TEXT("Opposing realm has no marker"), WarQuestMarkers::Resolve(Quests, Progress,
            Quest.Realm == TEXT("aegis") ? FName(TEXT("riftbound")) : FName(TEXT("aegis")),
            Quest.GiverZoneId, Quest.GiverNpcId, 1) == EWarQuestMarker::None);
        TestTrue(TEXT("Accept catalog quest"), WarQuests::Accept(Quest, Quest.Realm, Quest.GiverZoneId, 1, Progress, Error));
        TestTrue(TEXT("Accepted offer disappears"), At(Quest.GiverZoneId, Quest.GiverNpcId) == EWarQuestMarker::None);
        for (const auto& Objective : Quest.Objectives)
            for (int32 Kill = 0; Kill < Objective.Required; ++Kill)
                WarQuests::Kill(Quest, Quest.Realm, Objective.ZoneId, Objective.KillTarget, Progress);
        TestTrue(TEXT("Ready marker on correct recipient"), At(Quest.TurninZoneId, Quest.TurninNpcId) == EWarQuestMarker::TurnIn);
        TestTrue(TEXT("Ready marker is not on old capital giver"), At(Quest.GiverZoneId, Quest.GiverNpcId) == EWarQuestMarker::None);
        auto Additional = Quest; Additional.Id = TEXT("independent-offer");
        Additional.GiverNpcId = Quest.TurninNpcId; Additional.GiverZoneId = Quest.TurninZoneId;
        TestTrue(TEXT("Turn-in takes precedence over another offer"), WarQuestMarkers::Resolve({Additional, Quest}, Progress,
            Quest.Realm, Quest.TurninZoneId, Quest.TurninNpcId, 1) == EWarQuestMarker::TurnIn);
        TestEqual(TEXT("Marker query never adds accepted quests"), Progress.Num(), 1);
        TestEqual(TEXT("Marker query preserves ready status"), Progress[0].Status, FName(TEXT("ready_to_turn_in")));
        Progress[0].Status = TEXT("completed");
        TestTrue(TEXT("Next expedition offer unlocks"), At(Quest.TurninZoneId, Quest.TurninNpcId) == EWarQuestMarker::Offer);
    }
    return true;
}
#endif
