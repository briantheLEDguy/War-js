#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarInterfaceCatalog.h"
#include "WarControlSettings.h"
#include "WarGmRules.h"
#include "WarWorldEditHistory.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarInterfaceParityTest,"AegisWar.Foundation.InterfaceParity",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarInterfaceParityTest::RunTest(const FString& Parameters)
{
    TSharedPtr<FJsonObject> Root;
    const FString Json=TEXT(R"({"campaign":{"zones":[{"id":"a","name":"A"},{"id":"b","name":"B"},{"id":"a"}]},"maps":[{"id":"a","definition":{"size":100,"zoneTriggers":[{"id":"exit","targetZoneId":"b","x":12,"z":20},{"targetZoneId":"missing"}]}}],"wiki":{"sections":[{"id":"how","title":"How to"}],"pages":[{"id":"travel","sectionId":"how","title":"Travel","body":["Cross the campaign"],"tags":["Portals"],"tables":[{"title":"Routes","columns":["Name"],"rows":[{"cells":["Bastion"]}]}]}]}})");
    TestTrue(TEXT("Fixture parses"),FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root));
    const auto Catalog=FWarInterfaceCatalog::Parse(Root);
    TestEqual(TEXT("Zone identities unique"),Catalog.Zones.Num(),2);
    const auto* Zone=Catalog.FindZone(TEXT("a"));
    TestNotNull(TEXT("Source zone found"),Zone);
    if (Zone)
    {
        TestEqual(TEXT("Only known routes accepted"),Zone->Destinations.Num(),1);
        TestEqual(TEXT("Source coordinates projected consistently"),Zone->Markers[0].Position,FVector2D(12,-20));
    }
    TestEqual(TEXT("Case insensitive title/body/tag search"),Catalog.SearchGuide(TEXT("how"),TEXT("TRAVEL portals campaign")).Num(),1);
    TestEqual(TEXT("Table content searchable"),Catalog.SearchGuide(TEXT("how"),TEXT("Bastion")).Num(),1);
    TestEqual(TEXT("All search words required"),Catalog.SearchGuide(TEXT("how"),TEXT("travel absent")).Num(),0);
    TestEqual(TEXT("Section limits results"),Catalog.SearchGuide(TEXT("other"),TEXT("")).Num(),0);
    TestEqual(TEXT("Missing catalog recoverable"),FWarInterfaceCatalog::Parse(nullptr).Pages.Num(),0);
    TestFalse(TEXT("Blank character query rejected"),WarGmRules::ValidCharacterQuery(TEXT("  ")));
    TestFalse(TEXT("Oversized character query rejected"),WarGmRules::ValidCharacterQuery(FString::ChrN(33,'a')));
    TestFalse(TEXT("Multiline character query rejected"),WarGmRules::ValidCharacterQuery(TEXT("one\ntwo")));
    TestTrue(TEXT("Trimmed exact character query accepted"),WarGmRules::ValidCharacterQuery(TEXT(" Knight ")));
    TestFalse(TEXT("Wall is unsafe landing"),WarGmRules::IsSafeLandingNormal(FVector(1,0,0)));
    TestFalse(TEXT("Nonfinite ground is unsafe"),WarGmRules::IsSafeLandingNormal(FVector(0,0,std::numeric_limits<double>::infinity())));
    TestTrue(TEXT("Flat ground accepted"),WarGmRules::IsSafeLandingNormal(FVector::UpVector));
    TMap<FName,FKey> Bindings; FString Error;
    for (const auto& Entry:WarControls::Defaults()) Bindings.Add(Entry.Action,Entry.Key);
    TestTrue(TEXT("Unused key accepted"),WarControls::Validate(TEXT("Forward"),EKeys::P,Bindings,Error));
    TestFalse(TEXT("Conflicting key rejected"),WarControls::Validate(TEXT("Forward"),EKeys::S,Bindings,Error));
    TestFalse(TEXT("Menu escape cannot be reassigned"),WarControls::Validate(TEXT("Forward"),EKeys::Escape,Bindings,Error));
    TestFalse(TEXT("Axis cannot replace button"),WarControls::Validate(TEXT("Forward"),EKeys::MouseX,Bindings,Error));
    TestFalse(TEXT("Unknown actions rejected"),WarControls::Validate(TEXT("unknown"),EKeys::P,Bindings,Error));
    FWarWorldEditHistory History;
    TestTrue(TEXT("Baseline created"),History.Initialize({{TEXT("house"),FTransform::Identity,false}},Error));
    TestTrue(TEXT("Hide authored object"),History.Edit(TEXT("house"),FTransform::Identity,true,0,Error));
    TestTrue(TEXT("Add model"),History.Create(TEXT("gm_0123456789abcdef0123456789abcdef"),TEXT("house"),FTransform::Identity,1,Error));
    TestFalse(TEXT("Stale reset rejected"),History.Reset(1,Error));
    TestEqual(TEXT("Rejected reset preserves revision"),History.GetRevision(),2);
    TestTrue(TEXT("Reset accepted"),History.Reset(2,Error));
    TestFalse(TEXT("Baseline visible after reset"),History.Find(TEXT("house"))->bHidden);
    TestNull(TEXT("Created object removed"),History.Find(TEXT("gm_0123456789abcdef0123456789abcdef")));
    TestTrue(TEXT("Reset undoable"),History.Undo(false,3,Error));
    TestTrue(TEXT("Undo restores hidden state"),History.Find(TEXT("house"))->bHidden);
    TestNotNull(TEXT("Undo restores created model"),History.Find(TEXT("gm_0123456789abcdef0123456789abcdef")));
    TestTrue(TEXT("Reset redoable"),History.Undo(true,4,Error));
    TestNull(TEXT("Redo removes created model"),History.Find(TEXT("gm_0123456789abcdef0123456789abcdef")));
    return true;
}
#endif
