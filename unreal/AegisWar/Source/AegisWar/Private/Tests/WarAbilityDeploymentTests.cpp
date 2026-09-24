#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarAbilityDeploymentJournal.h"
#include "WarAbilityWorkshopDocument.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityDeploymentTest,"AegisWar.Foundation.AbilityDeploymentJournal",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarAbilityDeploymentTest::RunTest(const FString& Parameters)
{
    using namespace WarWorkshopJson;
    FString Json,Error;
    if (!TestTrue(TEXT("Staged baseline exists"),FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("Migration/content.json"))))) return false;
    FWarAbilityWorkshopDocument Document;
    TSharedPtr<FJsonObject> Manifest;
    if (!TestTrue(TEXT("Content manifest parses"),FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Manifest))) return false;
    if (!TestTrue(TEXT("Baseline compiles"),Document.Baseline(Manifest,Error))) return false;
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("Automation/AbilityDeployments")/FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FString First,Second,Original;
    {
        FWarAbilityDeploymentJournal Journal;
        if (!TestTrue(TEXT("Open exclusive journal"),Journal.Open(Folder,Error))) return false;
        FWarAbilityDeploymentJournal Other;
        TestFalse(TEXT("A second session cannot write the same deployment journal"),Other.Open(Folder,Error));
        TestTrue(TEXT("Save immutable version"),Journal.Queue(Document.Get(),TEXT("First"),First,Error));
        TestTrue(TEXT("Staging does not mark a version active"),Journal.Active().IsEmpty());
        TestFalse(TEXT("Wrong acknowledgement cannot activate"),Journal.Complete(FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower),Error));
        TestTrue(TEXT("Acknowledge activation"),Journal.Complete(First,Error));
        TestEqual(TEXT("Confirmed version pointer"),Journal.Active(),First);
        Original=Serialize(Journal.ReadVersion(First,Error));
        auto Changed=Clone(Document.Get()); Array(Changed,TEXT("abilities"))[0]->AsObject()->SetStringField(TEXT("name"),TEXT("Edited after first deploy"));
        TestTrue(TEXT("Queue second version"),Journal.Queue(Changed,TEXT("Second"),Second,Error));
        TestEqual(TEXT("First version was not mutated"),Serialize(Journal.ReadVersion(First,Error)),Original);
        TestFalse(TEXT("Reject version path traversal"),Journal.ReadVersion(TEXT("../journal"),Error).IsValid());
    }
    {
        FWarAbilityDeploymentJournal Reopened;
        TestTrue(TEXT("Reopen after process closes"),Reopened.Open(Folder,Error));
        TestEqual(TEXT("Interrupted staging retains last confirmed version"),Reopened.Active(),First);
        TestTrue(TEXT("Interrupted staging is cleared"),Reopened.Pending().IsEmpty());
        TestEqual(TEXT("Interrupted deployment is visibly failed"),Text(Reopened.Records()[0]->AsObject(),TEXT("phase")),FString(TEXT("failed")));
        TestTrue(TEXT("Failed staging retains immutable candidate for retry"),Reopened.ReadVersion(Second,Error).IsValid());
        TestTrue(TEXT("Rollback queues an existing immutable version"),Reopened.QueueExisting(First,TEXT("Rollback"),Error));
        TestTrue(TEXT("Rollback acknowledgement"),Reopened.Complete(First,Error));
        TestFalse(TEXT("Failure without pending deployment cannot alter confirmed history"),Reopened.Fail(TEXT("late error"),Error));
        TestEqual(TEXT("Version survives restart and rollback unchanged"),Serialize(Reopened.ReadVersion(First,Error)),Original);
    }
    TestTrue(TEXT("Write isolated corrupt-history fixture"),FFileHelper::SaveStringToFile(TEXT(R"({"schemaVersion":1,"activeVersion":"","pendingVersion":"","records":[null]})"),*(Folder/TEXT("journal.json"))));
    FWarAbilityDeploymentJournal Invalid;
    TestFalse(TEXT("Corrupt history returns a recoverable error"),Invalid.Open(Folder,Error));
    return true;
}
#endif
