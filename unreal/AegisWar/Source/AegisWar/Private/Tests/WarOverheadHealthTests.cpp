#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarOverheadHealth.h"
#include "WarFloatingCombatText.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarOverheadHealthTest, "AegisWar.Foundation.OverheadHealth",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarOverheadHealthTest::RunTest(const FString& Parameters)
{
    for (float Scale : {.8f, 1.f, 1.5f})
    {
        const FVector2D Head(500, 400), Viewport(1280, 720);
        const auto Bar = WarOverheadHealth::Bounds(Head, Viewport, Scale);
        TestTrue(TEXT("Visible recipient gets a bar"), Bar.bIsValid != 0);
        TestTrue(TEXT("Bar stays compact at each HUD scale"), Bar.GetSize().Equals(FVector2D(84, 10) * Scale, .001));
        TestTrue(TEXT("Bar is centered just above the head"), Bar.GetCenter().Equals(Head - FVector2D(0, 5 * Scale), .001));
        FWarFloatingCombatNumber Number;
        const float NumberBottom = Head.Y + (WarFloatingCombatText::Offset(Number).Y - WarOverheadHealth::CombatTextLift) * Scale;
        TestTrue(TEXT("New combat numbers clear the bar and border"), NumberBottom + Scale < Bar.Min.Y);
    }
    for (const FVector2D Head : {FVector2D(-1, 100), FVector2D(20, 100), FVector2D(1270, 100), FVector2D(400, 5), FVector2D(400, 721)})
        TestFalse(TEXT("Offscreen or partial bars are not clamped to screen edges"), WarOverheadHealth::Bounds(Head, FVector2D(1280, 720), 1).bIsValid != 0);
    TestFalse(TEXT("Invalid viewport rejected"), WarOverheadHealth::Bounds(FVector2D(500, 400), FVector2D::ZeroVector, 1).bIsValid != 0);
    TestFalse(TEXT("Invalid scale rejected"), WarOverheadHealth::Bounds(FVector2D(500, 400), FVector2D(1280, 720), 0).bIsValid != 0);
    FWarOverheadHealth Health; Health.Fraction = 1;
    TestFalse(TEXT("Missing recipients cannot invent health"), WarOverheadHealth::Read(nullptr, nullptr, Health));
    TestEqual(TEXT("Rejected snapshots clear stale health"), Health.Fraction, 0.f);
    return true;
}
#endif
