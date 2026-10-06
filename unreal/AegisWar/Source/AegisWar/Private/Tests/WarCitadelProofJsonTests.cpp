#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCitadelProofJson.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelProofJsonTest,"AegisWar.Foundation.CitadelProofJson",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelProofJsonTest::RunTest(const FString& Parameters)
{
    const FString Path=FPaths::ProjectSavedDir()/TEXT("CitadelProofJson-" )+FGuid::NewGuid().ToString()+TEXT(".json");
    auto Resolution=MakeShared<FJsonObject>(),Body=MakeShared<FJsonObject>(),Witness=MakeShared<FJsonObject>();
    Witness->SetStringField(TEXT("source"),TEXT("full live triangle witness"));
    Body->SetStringField(TEXT("decision"),TEXT("blocked"));Body->SetObjectField(TEXT("liveWitness"),Witness);
    Resolution->SetArrayField(TEXT("perBodyDecisions"),{MakeShared<FJsonValueObject>(Body)});
    Resolution->SetNumberField(TEXT("blockedBodyCount"),1);
    Resolution->SetStringField(TEXT("label"),TEXT("Bastion \u2014 \u00c6gis"));
    const auto Summary=WarCitadelProofJson::RejectedSeedSummary(Resolution);
    TestTrue(TEXT("Source witness is preserved without mutating its body"),Body->HasField(TEXT("liveWitness")));
    TestFalse(TEXT("Rejected seed summary removes unused triangle payload"),Summary->GetArrayField(TEXT("perBodyDecisions"))[0]->AsObject()->HasField(TEXT("liveWitness")));
    TestEqual(TEXT("Rejected seed retains every typed body and count"),Summary->GetNumberField(TEXT("blockedBodyCount")),1.);
    TestTrue(TEXT("Complete proof writes through a file archive"),WarCitadelProofJson::Save(Summary,Path));
    FString Text;TestTrue(TEXT("Streamed UTF-8 can be read by the standard file helper"),FFileHelper::LoadFileToString(Text,*Path));
    TSharedPtr<FJsonObject> Restored;
    TestTrue(TEXT("Streamed report is valid JSON"),FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Restored));
    if (Restored) TestEqual(TEXT("UTF-8 retains non-ASCII labels"),Restored->GetStringField(TEXT("label")),Resolution->GetStringField(TEXT("label")));
    IFileManager::Get().Delete(*Path);
    return true;
}
#endif
