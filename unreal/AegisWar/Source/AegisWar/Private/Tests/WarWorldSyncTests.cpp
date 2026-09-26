#include "Misc/AutomationTest.h"
#include "WarWorldSync.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWorldSyncTest, "AegisWar.Foundation.WorldSync",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarWorldSyncTest::RunTest(const FString& Parameters)
{
    FString Error; int32 Remote = INDEX_NONE;
    const FString Map = TEXT("/Game/War/Maps/crownward/Capital");
    FWarWorldEditHistory Local, Live;
    const TArray<FWarWorldEditObject> Objects = {{TEXT("house"), FTransform::Identity, false, TEXT("model:hash")}};
    Local.Initialize(Objects, Error); Live.Initialize(Objects, Error);
    FTransform Moved = FTransform::Identity; Moved.SetLocation(FVector(200,0,0));
    Live.Edit(TEXT("house"), Moved, false, 0, Error);
    const auto Response = [&](const FString& Document, double Revision, const FString& WorldMap) {
        auto Root = MakeShared<FJsonObject>(), Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("map"), WorldMap); Data->SetNumberField(TEXT("revision"), Revision);
        TSharedPtr<FJsonObject> Doc;
        if (FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Document), Doc)) Data->SetObjectField(TEXT("document"), Doc);
        else Data->SetField(TEXT("document"), MakeShared<FJsonValueNull>());
        Root->SetObjectField(TEXT("data"), Data); FString Text;
        FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Text)); return Text;
    };
    TestTrue(TEXT("Empty remote retains local document"), WarWorldSync::PreparePull(Response(TEXT(""),0,Map),Map,0,Local,Remote,Error));
    TestEqual(TEXT("Empty revision is observed"), Remote, 0);
    TestEqual(TEXT("Empty remote does not alter history"), Local.GetRevision(), 0);
    const FString Published = Response(Live.ExportDraft(),1,Map);
    TestFalse(TEXT("Wrong authored map rejected"), WarWorldSync::PreparePull(Published,Map+TEXT("Siege"),0,Local,Remote,Error));
    TestFalse(TEXT("Invalid fractional revision rejected"), WarWorldSync::PreparePull(Response(Live.ExportDraft(),1.5,Map),Map,0,Local,Remote,Error));
    TestFalse(TEXT("Missing remote document rejected"), WarWorldSync::PreparePull(Response(TEXT(""),1,Map),Map,0,Local,Remote,Error));
    TestTrue(TEXT("Live transforms pull through native validation"), WarWorldSync::PreparePull(Published,Map,0,Local,Remote,Error));
    TestTrue(TEXT("Live placement applied"), Local.Find(TEXT("house"))->Transform.Equals(Moved));
    TestFalse(TEXT("Edits made during request retained"), WarWorldSync::PreparePull(Published,Map,0,Local,Remote,Error));
    TestTrue(TEXT("Pull is undoable"), Local.Undo(false,1,Error));
    TestTrue(TEXT("Undo restores local layout"), Local.Find(TEXT("house"))->Transform.Equals(FTransform::Identity));
    FWarWorldEditHistory Incompatible;
    Incompatible.Initialize({{TEXT("house"), FTransform::Identity, false, TEXT("other:model")}},Error);
    TestFalse(TEXT("Missing/replaced models reject remote world"), WarWorldSync::PreparePull(Published,Map,0,Incompatible,Remote,Error));
    TestEqual(TEXT("Failed pull retains original history"), Incompatible.GetRevision(),0);
    return true;
}
#endif
