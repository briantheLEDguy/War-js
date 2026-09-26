#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWorldEditHistory.h"
#include "WarWorldEditPlacement.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCapitalExpansionGmTest, "AegisWar.Foundation.CapitalExpansionGM",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCapitalExpansionGmTest::RunTest(const FString& Parameters)
{
    const FTransform Original(FRotator(0,90,0),FVector(1601000,600200,-20000));
    FWarWorldEditHistory History; FString Error;
    TestTrue(TEXT("Riftspire templates use their authored world origin"),
        History.Initialize({{TEXT("rift_house"),Original,false,TEXT("reviewed-static-model")}},Error));
    FTransform Moved=Original; Moved.AddToTranslation(FVector(100,0,0));
    TestTrue(TEXT("Riftspire GM transform succeeds"),History.Edit(TEXT("rift_house"),Moved,false,0,Error));
    TestTrue(TEXT("Riftspire edit can undo"),History.Undo(false,1,Error));
    TestTrue(TEXT("Riftspire edit can redo"),History.Undo(true,2,Error));
    FWarWorldEditHistory Reloaded;
    Reloaded.Initialize(History.GetBaselineObjects(),Error);
    TestTrue(TEXT("Riftspire draft reload preserves the transform"),Reloaded.ImportDraft(History.ExportDraft(),0,Error)
        && Reloaded.Find(TEXT("rift_house"))->Transform.Equals(Moved));
    FTransform Far=Original; Far.AddToTranslation(FVector(200000,0,0));
    TestFalse(TEXT("An edit cannot leave its template neighbourhood"),
        History.Edit(TEXT("rift_house"),Far,false,History.GetRevision(),Error));
    const FBox Bounds(FVector(-200,-300,0),FVector(200,300,600));
    const FVector Surface=Original.GetLocation()+FVector(500,0,0);
    TestTrue(TEXT("Riftspire ground placement succeeds"),WarWorldEditPlacement::AtSurface(Original,Bounds,Surface).IsSet());
    TestTrue(TEXT("Riftspire wall and floor contact succeeds"),
        WarWorldEditPlacement::AtContact(Original,Bounds,Surface,FVector::UpVector,50).IsSet());
    TestTrue(TEXT("Riftspire rows can calculate their spacing"),WarWorldEditPlacement::RowStep(Original,Bounds,false,25).IsSet());
    FTransform Exact=Original;
    TestTrue(TEXT("Riftspire numeric coordinates remain editable in metres"),
        WarWorldEditPlacement::SetComponent(Exact,0,16011.) && Exact.GetLocation().X==1601100.);
    TestFalse(TEXT("Placement retains a bounded distance from the template"),
        WarWorldEditPlacement::AtSurface(Original,Bounds,Surface+FVector(200000,0,0)).IsSet());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCapitalReplacementTest, "AegisWar.Foundation.CapitalReplacementDrafts",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCapitalReplacementTest::RunTest(const FString& Parameters)
{
    const FWarWorldEditObject Old{TEXT("house"),FTransform(FVector(1000,0,0)),false,TEXT("old-reviewed-house")};
    const FWarWorldEditObject New{TEXT("house"),FTransform(FRotator(0,90,0),FVector(1100,0,0)),false,TEXT("new-reviewed-house")};
    const FWarWorldEditObject Barrel{TEXT("barrel"),FTransform(FVector(3000,0,0)),false,TEXT("unchanged-barrel")};
    FWarWorldEditHistory Previous,Current; FString Error;
    Previous.Initialize({Old,Barrel},Error); Current.Initialize({New,Barrel},Error);
    TestFalse(TEXT("A draft cannot admit a replacement itself"),Current.ImportDraft(Previous.ExportDraft(),0,Error));
    TestFalse(TEXT("Replacement admission must match the installed static template"),
        Current.AllowBaselineReplacement(Old,TEXT("arbitrary-model"),Error));
    TestTrue(TEXT("Reviewed old and current models can be paired"),Current.AllowBaselineReplacement(Old,New.SourceIdentity,Error));
    FTransform MovedBarrel=Barrel.Transform; MovedBarrel.AddToTranslation(FVector(0,100,0));
    Previous.Edit(Barrel.Id,MovedBarrel,true,0,Error);
    const FName Created(*(TEXT("gm_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    Previous.Create(Created,Barrel.Id,MovedBarrel,Previous.GetRevision(),Error);
    TestTrue(TEXT("Unchanged old houses migrate without discarding unrelated edits or creations"),
        Current.ImportDraft(Previous.ExportDraft(),0,Error));
    TestTrue(TEXT("Replacement adopts the reviewed geometry placement"),Current.Find(Old.Id)->Transform.Equals(New.Transform)
        && Current.Find(Old.Id)->SourceIdentity==New.SourceIdentity);
    TestTrue(TEXT("Owner barrel transform and visibility survive"),Current.Find(Barrel.Id)->Transform.Equals(MovedBarrel)
        && Current.Find(Barrel.Id)->bHidden && Current.Find(Created));
    FWarWorldEditHistory Reloaded; Reloaded.Initialize({New,Barrel},Error);
    TestTrue(TEXT("A newly saved draft needs no legacy mapping"),Reloaded.ImportDraft(Current.ExportDraft(),0,Error));
    FTransform Edited=Old.Transform; Edited.AddToTranslation(FVector(25,0,0));
    Previous.Edit(Old.Id,Edited,false,Previous.GetRevision(),Error);
    const FString Before=Current.ExportDraft(); const int32 Revision=Current.GetRevision();
    TestFalse(TEXT("Owner edits on a replaced house fail closed"),Current.ImportDraft(Previous.ExportDraft(),Revision,Error));
    TestEqual(TEXT("Rejected migration preserves the current document"),Current.ExportDraft(),Before);
    Previous.Edit(Old.Id,Old.Transform,false,Previous.GetRevision(),Error);
    const FString Forged=Previous.ExportDraft().Replace(TEXT("old-reviewed-house"),TEXT("unreviewed-house"));
    TestFalse(TEXT("Legacy source fingerprints cannot be forged"),Current.ImportDraft(Forged,Revision,Error));
    Previous.Create(FName(*(TEXT("gm_")+FGuid::NewGuid().ToString(EGuidFormats::Digits))),Old.Id,Old.Transform,Previous.GetRevision(),Error);
    TestFalse(TEXT("Existing copies of a replaced template require explicit reconciliation"),
        Current.ImportDraft(Previous.ExportDraft(),Revision,Error));
    return true;
}
#endif
