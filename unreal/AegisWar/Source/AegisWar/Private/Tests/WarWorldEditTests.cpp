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
    return true;
}
#endif
