#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarT1TraversalProof.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarT1TraversalFixtureTest, "AegisWar.Foundation.T1TraversalFixture",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarT1TraversalFixtureTest::RunTest(const FString& Parameters)
{
    TestTrue(TEXT("Bounded run selector"), UWarT1TraversalProof::ValidSelector(TEXT("123-456/sunmeadow_march.json")));
    for (const FString Selector : {TEXT("../sunmeadow_march.json"), TEXT("123/../cinderfen_outskirts.json"),
        TEXT("123/aegis_capital.json"), TEXT("C:/owner.json"), TEXT("/sunmeadow_march.json"), TEXT("123\\sunmeadow_march.json")})
        TestFalse(TEXT("Cannot select another file"), UWarT1TraversalProof::ValidSelector(Selector));
    TestTrue(TEXT("Private home study"), UWarT1TraversalProof::ValidCandidate(
        TEXT("/Game/WorldRebuild/T1Redesign_Homes_abc_123/sunmeadow_march/Review"), TEXT("sunmeadow_march")));
    TestTrue(TEXT("Private material study"), UWarT1TraversalProof::ValidCandidate(
        TEXT("/Game/WorldRebuild/T1Redesign_Materials_abc_123/cinderfen_outskirts/Review"), TEXT("cinderfen_outskirts")));
    TestFalse(TEXT("Unrecognized study excluded"), UWarT1TraversalProof::ValidCandidate(
        TEXT("/Game/WorldRebuild/T1Redesign_Unknown_abc_123/sunmeadow_march/Review"), TEXT("sunmeadow_march")));
    TestFalse(TEXT("Capital excluded"), UWarT1TraversalProof::ValidCandidate(TEXT("/Game/WorldRebuild/aegis_capital/Review"), TEXT("sunmeadow_march")));
    TestFalse(TEXT("Another zone excluded"), UWarT1TraversalProof::ValidCandidate(
        TEXT("/Game/WorldRebuild/T1Redesign_Homes_abc_123/cinderfen_outskirts/Review"), TEXT("sunmeadow_march")));
    TestFalse(TEXT("Owner layer excluded"), UWarT1TraversalProof::ValidCandidate(
        TEXT("/Game/WorldRebuild/T1Redesign_Homes_abc_123/sunmeadow_march/Authored"), TEXT("sunmeadow_march")));
    TestFalse(TEXT("Later batch excluded"), UWarT1TraversalProof::ValidCandidate(
        TEXT("/Game/WorldRebuild/T1Redesign_Homes_abc_123/brightfen_approach/Review"), TEXT("brightfen_approach")));
    return true;
}
#endif
