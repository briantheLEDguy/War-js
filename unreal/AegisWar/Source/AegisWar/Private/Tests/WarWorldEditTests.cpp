#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWorldEditHistory.h"
#include "WarWorldEditPlacement.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWorldEditHistoryTest, "AegisWar.Foundation.WorldEditHistory",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarWorldEditHistoryTest::RunTest(const FString& Parameters)
{
    const FTransform GridInput(FRotator(12, 44, -8), FVector(125, -175, 73.2), FVector(2, -3, 4));
    const auto Snapped = WarWorldEditPlacement::SnapTransform(GridInput, 50, 90);
    TestTrue(TEXT("Browser half-grid rounding handles negative coordinates"), Snapped.GetLocation().Equals(FVector(150, -150, 73.2)));
    TestTrue(TEXT("Snapping preserves model handedness and authored scale"), Snapped.GetScale3D().Equals(GridInput.GetScale3D()));
    TestTrue(TEXT("Yaw snaps without flattening pitch/roll"), Snapped.GetRotation().Equals(FRotator(12, 0, -8).Quaternion(), 0.00001));
    TestTrue(TEXT("Disabled snapping retains the exact transform"), WarWorldEditPlacement::SnapTransform(GridInput, 0, 0).Equals(GridInput));
    TestTrue(TEXT("Invalid grid and angle settings are inert"), WarWorldEditPlacement::SnapTransform(GridInput, -50, 361).Equals(GridInput));
    const auto Placed = WarWorldEditPlacement::SnapHorizontal(FVector(-151, 249, 27.4), 100);
    TestTrue(TEXT("Ground height is never quantized"), Placed.Equals(FVector(-200, 200, 27.4)));
    FWarWorldEditHistory History; FString Error;
    FTransform Exact = GridInput;
    TestTrue(TEXT("Exact position accepts metres"), WarWorldEditPlacement::SetComponent(Exact, 0, -12.345));
    TestTrue(TEXT("Metres convert to Unreal centimetres"), FMath::IsNearlyEqual(Exact.GetLocation().X, -1234.5));
    TestTrue(TEXT("Other position axes retained"), Exact.GetLocation().Y == GridInput.GetLocation().Y && Exact.GetLocation().Z == GridInput.GetLocation().Z);
    TestTrue(TEXT("Exact rotation accepts pitch"), WarWorldEditPlacement::SetComponent(Exact, 3, 25));
    TestTrue(TEXT("Yaw and roll retained"), Exact.GetRotation().Equals(FRotator(25, 44, -8).Quaternion(), 0.00001));
    TestTrue(TEXT("Nonuniform scale accepts magnitude"), WarWorldEditPlacement::SetComponent(Exact, 7, 1.25));
    TestTrue(TEXT("Mirrored imported scale remains mirrored"), Exact.GetScale3D().Equals(FVector(2, -1.25, 4)));
    TestEqual(TEXT("Displayed scale is positive magnitude"), WarWorldEditPlacement::ComponentValue(Exact, 7).GetValue(), 1.25);
    const FTransform BeforeInvalid = Exact;
    TestFalse(TEXT("Invisible exact scale rejected"), WarWorldEditPlacement::SetComponent(Exact, 6, 0));
    TestFalse(TEXT("Exact scale cannot invert handedness"), WarWorldEditPlacement::SetComponent(Exact, 7, -1));
    TestFalse(TEXT("Out-of-bounds position rejected"), WarWorldEditPlacement::SetComponent(Exact, 2, 1000.01));
    TestFalse(TEXT("Excessive rotation rejected"), WarWorldEditPlacement::SetComponent(Exact, 4, 361));
    TestFalse(TEXT("Unknown transform component rejected"), WarWorldEditPlacement::SetComponent(Exact, 9, 1));
    TestFalse(TEXT("Nonfinite transform component rejected"), WarWorldEditPlacement::SetComponent(Exact, 1, std::numeric_limits<double>::infinity()));
    TestTrue(TEXT("Rejected numeric changes leave transform intact"), Exact.Equals(BeforeInvalid));
    FWarWorldEditHistory ExactHistory;
    ExactHistory.Initialize({ { TEXT("precise"), GridInput, false } }, Error);
    TestTrue(TEXT("Exact transform enters revisioned history"), ExactHistory.Edit(TEXT("precise"), Exact, false, 0, Error));
    TestTrue(TEXT("Exact edit can be undone"), ExactHistory.Undo(false, 1, Error));
    TestTrue(TEXT("Undo restores every axis"), ExactHistory.Find(TEXT("precise"))->Transform.Equals(GridInput));
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
    FWarWorldEditHistory Expanded;
    const TArray<FWarWorldEditObject> ExpandedObjects = { Objects[0], { TEXT("new_import"), Original, false } };
    Expanded.Initialize(ExpandedObjects, Error);
    TestTrue(TEXT("Earlier construction draft loads after additive city import"), Expanded.ImportDraft(ConstructionDraft, 0, Error));
    TestEqual(TEXT("Newly imported object count reported"), Expanded.GetLoadedBaselineAdditions(), 1);
    TestEqual(TEXT("Authored additions and player construction both retained"), Expanded.GetObjects().Num(), 3);
    TestTrue(TEXT("New baseline object remains unchanged"), Expanded.Find(TEXT("new_import"))->Transform.Equals(Original));
    TestNotNull(TEXT("Player construction retained across import"), Expanded.Find(Created));
    TestTrue(TEXT("Additive draft load remains undoable"), Expanded.Undo(false, 1, Error));
    TestEqual(TEXT("Undo restores expanded baseline"), Expanded.GetObjects().Num(), 2);
    TestTrue(TEXT("Legacy edit-only draft loads after additive import"), Expanded.ImportDraft(LegacyDraft, 2, Error));
    FWarWorldEditHistory ChangedModel;
    ChangedModel.Initialize({ { TEXT("house"), Original, false, TEXT("changed:model") }, ExpandedObjects[1] }, Error);
    TestFalse(TEXT("Addition does not mask changed model conflict"), ChangedModel.ImportDraft(ConstructionDraft, 0, Error));
    FWarWorldEditHistory RemovedObject;
    RemovedObject.Initialize({ ExpandedObjects[1] }, Error);
    TestFalse(TEXT("Removed authored object rejects load"), RemovedObject.ImportDraft(ConstructionDraft, 0, Error));
    TestEqual(TEXT("Conflict leaves current document unchanged"), RemovedObject.GetRevision(), 0);
    FWarWorldEditHistory RoundTrip;
    RoundTrip.Initialize(ExpandedObjects, Error);
    TestTrue(TEXT("Expanded draft exports its new baseline"), RoundTrip.ImportDraft(Expanded.ExportDraft(), 0, Error));
    TestEqual(TEXT("Reconciled baseline does not repeatedly report additions"), RoundTrip.GetLoadedBaselineAdditions(), 0);
    return true;
}
#endif
