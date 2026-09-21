#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarMovementInput.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMovementInputTest, "AegisWar.Foundation.MovementInput",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarMovementInputTest::RunTest(const FString& Parameters)
{
    FWarMovementInput Input;
    TestTrue(TEXT("No intent at rest"), Input.Resolve(0, 0, false, false, true, false).IsZero());
    Input.Toggle(true);
    TestTrue(TEXT("Autorun moves forward"), Input.Resolve(0, 0, false, false, true, false).Equals(FVector2D(1, 0)));
    TestTrue(TEXT("Modal pauses autorun"), Input.Resolve(0, 0, false, true, false, false).IsZero());
    Input.Toggle(false); TestTrue(TEXT("Blocked toggle does not change mode"), Input.bAutoRun);
    TestTrue(TEXT("Closing modal resumes prior mode"), Input.Resolve(0, 0, false, false, true, false).Equals(FVector2D(1, 0)));
    for (const auto Axis : {FVector2D(1, 0), FVector2D(-1, 0), FVector2D(0, 1), FVector2D(0, -1), FVector2D(0, 0)})
    {
        Input.bAutoRun = true;
        TestTrue(TEXT("Manual input replaces autorun"), Input.Resolve(Axis.X, Axis.Y, true, false, true, false).Equals(Axis));
        TestFalse(TEXT("Every movement key cancels autorun, including opposing keys"), Input.bAutoRun);
    }
    TestTrue(TEXT("Both mouse buttons move forward"), Input.Resolve(0, 0, false, true, true, false).Equals(FVector2D(1, 0)));
    TestTrue(TEXT("Backward cancels both-button forward"), Input.Resolve(-1, 0, true, true, true, false).IsZero());
    TestTrue(TEXT("Diagonal keyboard speed is normalized"), FMath::IsNearlyEqual(Input.Resolve(1, 1, true, false, true, false).Size(), 1.0));
    const auto Combined = Input.Resolve(1, 1, true, true, true, false);
    TestTrue(TEXT("Combined keyboard/mouse direction matches browser sum"), FMath::IsNearlyEqual(Combined.X / Combined.Y, 2.0));
    TestTrue(TEXT("Combined input cannot increase speed"), FMath::IsNearlyEqual(Combined.Size(), 1.0));
    Input.Toggle(true); Input.Resolve(0, 0, false, false, false, true);
    TestFalse(TEXT("Death/flying clears autorun even while blocked"), Input.bAutoRun);
    TestTrue(TEXT("Invalid axes produce no movement"), Input.Resolve(std::numeric_limits<double>::quiet_NaN(), 0, false, true, true, false).IsZero());
    return true;
}
#endif
