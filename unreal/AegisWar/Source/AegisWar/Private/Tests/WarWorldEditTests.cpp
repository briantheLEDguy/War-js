#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWorldEditHistory.h"
#include "WarWorldEditPlacement.h"
#include "WarWorldEditMap.h"
#include <limits>
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWorldEditHistoryTest, "AegisWar.Foundation.WorldEditHistory",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarWorldEditHistoryTest::RunTest(const FString& Parameters)
{
    const FString FinalMap = TEXT("/Game/Capitals/crownward/FinalAppearance/City");
    TestTrue(TEXT("Selected owner city supports the GM workbench"), WarWorldEditMap::IsSupported(FinalMap, FinalMap));
    TestFalse(TEXT("Unselected preview is not a workbench"), WarWorldEditMap::IsSupported(TEXT("/Game/Capitals/crownward/Other/City"), FinalMap));
    TestFalse(TEXT("Arbitrary configured maps cannot become workbenches"), WarWorldEditMap::IsSupported(TEXT("/Game/Other"), TEXT("/Game/Other")));
    TestTrue(TEXT("Legacy authored proof remains available"), WarWorldEditMap::IsSupported(TEXT("/Game/Capitals/aegis_capital/AegisCapital_Workbench"), FinalMap));
    const FTransform GridInput(FRotator(12, 44, -8), FVector(125, -175, 73.2), FVector(2, -3, 4));
    const auto Snapped = WarWorldEditPlacement::SnapTransform(GridInput, 50, 90);
    TestTrue(TEXT("Browser half-grid rounding handles negative coordinates"), Snapped.GetLocation().Equals(FVector(150, -150, 73.2)));
    TestTrue(TEXT("Snapping preserves model handedness and authored scale"), Snapped.GetScale3D().Equals(GridInput.GetScale3D()));
    TestTrue(TEXT("Yaw snaps without flattening pitch/roll"), Snapped.GetRotation().Equals(FRotator(12, 0, -8).Quaternion(), 0.00001));
    TestTrue(TEXT("Disabled snapping retains the exact transform"), WarWorldEditPlacement::SnapTransform(GridInput, 0, 0).Equals(GridInput));
    TestTrue(TEXT("Invalid grid and angle settings are inert"), WarWorldEditPlacement::SnapTransform(GridInput, -50, 361).Equals(GridInput));
    const auto Placed = WarWorldEditPlacement::SnapHorizontal(FVector(-151, 249, 27.4), 100);
    TestTrue(TEXT("Ground height is never quantized"), Placed.Equals(FVector(-200, 200, 27.4)));
    const FBox OffsetBounds(FVector(100,-230,-15), FVector(400,70,285));
    const FVector Contact(1200,-2300,417);
    for (const FTransform Basis : { FTransform::Identity,
        FTransform(FRotator(25,90,-15), FVector(800,900,700), FVector(.75,-2,1.5)),
        FTransform(FRotator(0,180,0), FVector::ZeroVector, FVector(2,3,.25)) })
    {
        const auto SurfaceTransform = WarWorldEditPlacement::AtSurface(Basis, OffsetBounds, Contact);
        TestTrue(TEXT("Offset authored pivot supports placement"), SurfaceTransform.IsSet());
        if (!SurfaceTransform.IsSet()) continue;
        const FBox Actual = OffsetBounds.TransformBy(SurfaceTransform.GetValue());
        TestTrue(TEXT("Bounds centre lands on selected horizontal point"), FVector::Dist2D(Actual.GetCenter(),Contact) < .001);
        TestTrue(TEXT("Lowest oriented point rests on the surface"), FMath::IsNearlyEqual(Actual.Min.Z, Contact.Z, .001));
        TestTrue(TEXT("Surface placement preserves orientation and mirrored scale"),
            SurfaceTransform->GetRotation().Equals(Basis.GetRotation()) && SurfaceTransform->GetScale3D().Equals(Basis.GetScale3D()));
    }
    TestFalse(TEXT("Missing mesh bounds cannot place a fallback"), WarWorldEditPlacement::AtSurface(FTransform::Identity,FBox(ForceInit),Contact).IsSet());
    TestFalse(TEXT("Invalid hit cannot alter placement"), WarWorldEditPlacement::AtSurface(FTransform::Identity,OffsetBounds,
        FVector(std::numeric_limits<double>::quiet_NaN(),0,0)).IsSet());
    TestFalse(TEXT("Out-of-world placement fails"), WarWorldEditPlacement::AtSurface(FTransform::Identity,OffsetBounds,FVector(200000,0,0)).IsSet());
    const FTransform RowBasis(FRotator(0,45,0),FVector::ZeroVector,FVector(2,-3,1));
    const auto RowStep=WarWorldEditPlacement::RowStep(RowBasis,OffsetBounds,false,25);
    const auto CrossStep=WarWorldEditPlacement::RowStep(RowBasis,OffsetBounds,true,0);
    TestTrue(TEXT("Diagonal spacing uses oriented model width, not larger world box"), RowStep.IsSet()
        && FMath::IsNearlyEqual(RowStep->Size(),625.,.001) && FMath::IsNearlyEqual(RowStep->Z,0.));
    TestTrue(TEXT("Mirrored local Y retains correct width and perpendicular direction"), CrossStep.IsSet()
        && FMath::IsNearlyEqual(CrossStep->Size(),900.,.001) && RowStep.IsSet()
        && FMath::IsNearlyZero(FVector::DotProduct(*RowStep,*CrossStep),.001));
    TestFalse(TEXT("Negative row gaps cannot overlap pieces"), WarWorldEditPlacement::RowStep(RowBasis,OffsetBounds,false,-1).IsSet());
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
        ConstructionDraft.Replace(TEXT("\"templateId\":\"house\""), TEXT("\"templateId\":\"unregistered\"")), 1, Error));
    TestTrue(TEXT("Undo removes created object from current state"), Construction.Undo(false, 1, Error));
    TestNull(TEXT("Creation removed by undo"), Construction.Find(Created));
    TestTrue(TEXT("Redo restores created object"), Construction.Undo(true, 2, Error));
    TestNotNull(TEXT("Created object restored by redo"), Construction.Find(Created));
    FWarWorldEditHistory Batch;
    Batch.Initialize(Objects,Error);
    const FName SecondCreated(TEXT("gm_1123456789abcdef0123456789abcdef"));
    TArray<FWarWorldEditCreation> Additions={{Created,TEXT("house"),Moved},{SecondCreated,TEXT("unknown"),Moved}};
    TestFalse(TEXT("Invalid last row piece rejects the entire construction"),Batch.CreateBatch(Additions,0,Error));
    TestEqual(TEXT("Failed batch leaves objects and revision intact"),Batch.GetObjects().Num(),1);
    TestEqual(TEXT("Failed batch revision"),Batch.GetRevision(),0);
    Additions[1].TemplateId=TEXT("house");
    TestTrue(TEXT("Valid row creates every piece"),Batch.CreateBatch(Additions,0,Error));
    const FString BatchDraft=Batch.ExportDraft();
    TestFalse(TEXT("Stale row is rejected"),Batch.CreateBatch(Additions,0,Error));
    TestTrue(TEXT("One undo removes the whole row"),Batch.Undo(false,1,Error));
    TestEqual(TEXT("Whole row removed"),Batch.GetObjects().Num(),1);
    TestTrue(TEXT("One redo restores the whole row"),Batch.Undo(true,2,Error));
    TestEqual(TEXT("Whole row restored"),Batch.GetObjects().Num(),3);
    FWarWorldEditHistory BatchReload; BatchReload.Initialize(Objects,Error);
    TestTrue(TEXT("Row survives fresh draft import"),BatchReload.ImportDraft(BatchDraft,0,Error));
    TestEqual(TEXT("Every row piece reloaded"),BatchReload.GetObjects().Num(),3);
    FWarWorldEditHistory Legacy;
    Legacy.Initialize(Objects, Error);
    TSharedPtr<FJsonObject> LegacyRoot, LegacyBase;
    TestTrue(TEXT("Legacy draft fixture parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Legacy.ExportDraft()), LegacyRoot));
    TestTrue(TEXT("Legacy baseline fixture parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(LegacyRoot->GetStringField(TEXT("baseline"))), LegacyBase));
    FString PrettyBase, LegacyDraft;
    FJsonSerializer::Serialize(LegacyBase, TJsonWriterFactory<>::Create(&PrettyBase));
    LegacyRoot->SetStringField(TEXT("baseline"), PrettyBase);
    LegacyRoot->SetNumberField(TEXT("schemaVersion"), 1);
    FJsonSerializer::Serialize(LegacyRoot, TJsonWriterFactory<>::Create(&LegacyDraft));
    TestTrue(TEXT("Legacy fixture has pretty baseline whitespace"), PrettyBase.Contains(TEXT("\n")));
    TestTrue(TEXT("Version-one edit-only drafts remain readable"), Legacy.ImportDraft(LegacyDraft, 0, Error));
    FWarWorldEditHistory StableModels;
    StableModels.Initialize({ { TEXT("first"), Original, false, TEXT("mesh:hash") },
        { TEXT("second"), Original, false, TEXT("mesh:hash") } }, Error);
    StableModels.Create(Created, TEXT("first"), Moved, 0, Error);
    TestFalse(TEXT("A draft cannot change a live object's trusted template"), StableModels.ImportDraft(
        StableModels.ExportDraft().Replace(TEXT("\"templateId\":\"first\""), TEXT("\"templateId\":\"second\"")), 1, Error));
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
    TArray<FWarWorldEditObject> CityObjects;
    for (int32 Index = 0; Index < 10000; ++Index)
        CityObjects.Add({ FName(*FString::Printf(TEXT("crownward_module_%04d"), Index)), Original, false,
            TEXT("/Game/LicensedKits/Crownward/SM_StoneWall:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef") });
    FWarWorldEditHistory LargeCity, ReloadedCity;
    TestTrue(TEXT("City baseline initializes"), LargeCity.Initialize(CityObjects, Error));
    TestTrue(TEXT("Fresh city baseline initializes"), ReloadedCity.Initialize(CityObjects, Error));
    const FString CityDraft = LargeCity.ExportDraft();
    TestTrue(TEXT("City exceeds the former draft cap"), CityDraft.Len() > 2000000);
    TestTrue(TEXT("Full city draft remains below byte cap"), FTCHARToUTF8(*CityDraft).Length() < 8000000);
    TestTrue(TEXT("Large city draft round trips"), ReloadedCity.ImportDraft(CityDraft, 0, Error));
    TestEqual(TEXT("All city modules survive draft reload"), ReloadedCity.GetObjects().Num(), 10000);
    TestFalse(TEXT("Oversized input remains bounded"), ReloadedCity.ImportDraft(FString::ChrN(8000001, TEXT(' ')), 1, Error));
    return true;
}
#endif
