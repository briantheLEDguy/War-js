#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWorldEditHistory.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWorldEditHistoryTest, "AegisWar.Foundation.WorldEditHistory",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarWorldEditHistoryTest::RunTest(const FString& Parameters)
{
    FWarWorldEditHistory History; FString Error;
    const FTransform Original(FQuat::Identity, FVector(100, 200, 0), FVector(1, -1, 1));
    const TArray<FWarWorldEditObject> Objects = { { TEXT("house"), Original, false } };
    TestTrue(TEXT("Authored basis accepted"), History.Initialize(Objects, Error));
    FTransform Moved = Original; Moved.AddToTranslation(FVector(100, 0, 0));
    TestFalse(TEXT("Unknown identity rejected"), History.Edit(TEXT("invented"), Moved, false, 0, Error));
    TestTrue(TEXT("Move committed"), History.Edit(TEXT("house"), Moved, false, 0, Error));
    TestFalse(TEXT("Stale edit rejected"), History.Edit(TEXT("house"), Original, false, 0, Error));
    TestEqual(TEXT("Rejected edit retains revision"), History.GetRevision(), 1);
    TestTrue(TEXT("Undo restores position"), History.Undo(false, 1, Error));
    TestTrue(TEXT("Original transform restored"), History.Find(TEXT("house"))->Transform.Equals(Original));
    TestTrue(TEXT("Redo reapplies move"), History.Undo(true, 2, Error));
    TestTrue(TEXT("Hide is reversible state"), History.Edit(TEXT("house"), Moved, true, 3, Error));
    const FString Draft = History.ExportDraft();
    FWarWorldEditHistory Reloaded;
    TestTrue(TEXT("New session baseline"), Reloaded.Initialize(Objects, Error));
    TestTrue(TEXT("Draft round trip"), Reloaded.ImportDraft(Draft, 0, Error));
    TestTrue(TEXT("Hidden state restored"), Reloaded.Find(TEXT("house"))->bHidden);
    TestTrue(TEXT("Draft load can be undone"), Reloaded.Undo(false, 1, Error));
    TestTrue(TEXT("New branch edit"), Reloaded.Edit(TEXT("house"), Original, true, 2, Error));
    TestFalse(TEXT("New edit invalidates redo"), Reloaded.Undo(true, 3, Error));
    FTransform Invalid = Original; Invalid.SetScale3D(FVector(1, 1, 1));
    TestFalse(TEXT("Handedness cannot be changed"), Reloaded.Edit(TEXT("house"), Invalid, false, 3, Error));
    Invalid = Original; Invalid.SetScale3D(FVector(0, -1, 1));
    TestFalse(TEXT("Invisible zero scale rejected"), Reloaded.Edit(TEXT("house"), Invalid, false, 3, Error));
    Invalid = Original; Invalid.SetLocation(FVector(100001, 0, 0));
    TestFalse(TEXT("Unbounded world position rejected"), Reloaded.Edit(TEXT("house"), Invalid, false, 3, Error));
    TestFalse(TEXT("Malformed draft rejected atomically"), Reloaded.ImportDraft(TEXT("{}"), 3, Error));
    TestEqual(TEXT("No rejected operation changes revision"), Reloaded.GetRevision(), 3);
    FWarWorldEditHistory DifferentWorld;
    TestTrue(TEXT("Other authored revision"), DifferentWorld.Initialize({ { TEXT("house"), Moved, false } }, Error));
    TestFalse(TEXT("Old draft cannot overwrite different base"), DifferentWorld.ImportDraft(Draft, 0, Error));
    TestFalse(TEXT("Duplicate baseline rejected"), DifferentWorld.Initialize({ Objects[0], Objects[0] }, Error));
    FWarWorldEditHistory Construction;
    TestTrue(TEXT("Construction baseline"), Construction.Initialize(Objects, Error));
    const FName Created(TEXT("gm_0123456789abcdef0123456789abcdef"));
    TestFalse(TEXT("Unregistered template rejected"), Construction.Create(Created, TEXT("unknown"), Moved, 0, Error));
    TestFalse(TEXT("Arbitrary created identity rejected"), Construction.Create(TEXT("arbitrary"), TEXT("house"), Moved, 0, Error));
    TestTrue(TEXT("New authored-model object created"), Construction.Create(Created, TEXT("house"), Moved, 0, Error));
    TestEqual(TEXT("Construction retains authored baseline"), Construction.GetObjects().Num(), 2);
    TestFalse(TEXT("Created identity cannot be reused"), Construction.Create(Created, TEXT("house"), Moved, 1, Error));
    const FString ConstructionDraft = Construction.ExportDraft();
    FWarWorldEditHistory Fresh;
    Fresh.Initialize(Objects, Error);
    TestTrue(TEXT("New object survives fresh draft load"), Fresh.ImportDraft(ConstructionDraft, 0, Error));
    if (const auto* Restored = Fresh.Find(Created)) TestEqual(TEXT("Reload retains template identity"), Restored->TemplateId, FName(TEXT("house")));
    else AddError(TEXT("Missing restored construction object."));
    TestFalse(TEXT("Draft cannot select an unregistered template"), Fresh.ImportDraft(
        ConstructionDraft.Replace(TEXT("\"templateId\": \"house\""), TEXT("\"templateId\": \"unregistered\"")), 1, Error));
    TestTrue(TEXT("Undo removes created object from current state"), Construction.Undo(false, 1, Error));
    TestNull(TEXT("Creation removed by undo"), Construction.Find(Created));
    TestTrue(TEXT("Redo restores created object"), Construction.Undo(true, 2, Error));
    TestNotNull(TEXT("Created object restored by redo"), Construction.Find(Created));
    FWarWorldEditHistory Legacy;
    Legacy.Initialize(Objects, Error);
    const FString LegacyDraft = Legacy.ExportDraft().Replace(TEXT("\"schemaVersion\": 2"), TEXT("\"schemaVersion\": 1"));
    TestTrue(TEXT("Legacy fixture has version one"), LegacyDraft.Contains(TEXT("\"schemaVersion\": 1")));
    TestTrue(TEXT("Version-one edit-only drafts remain readable"), Legacy.ImportDraft(LegacyDraft, 0, Error));
    FWarWorldEditHistory StableModels;
    StableModels.Initialize({ { TEXT("first"), Original, false, TEXT("mesh:hash") },
        { TEXT("second"), Original, false, TEXT("mesh:hash") } }, Error);
    StableModels.Create(Created, TEXT("first"), Moved, 0, Error);
    TestFalse(TEXT("A draft cannot change a live object's trusted template"), StableModels.ImportDraft(
        StableModels.ExportDraft().Replace(TEXT("\"templateId\": \"first\""), TEXT("\"templateId\": \"second\"")), 1, Error));
    return true;
}
#endif
