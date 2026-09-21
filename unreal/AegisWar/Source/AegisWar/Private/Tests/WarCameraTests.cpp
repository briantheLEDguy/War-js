#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCameraRules.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCameraTest, "AegisWar.Foundation.CameraControls",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCameraTest::RunTest(const FString& Parameters)
{
    FWarCameraState Camera;
    TestEqual(TEXT("Seven metre outdoor default"), Camera.Distance, 700.0);
    Camera.WheelPixels(-10000); TestEqual(TEXT("Outdoor near limit"), Camera.Distance, 300.0);
    Camera.WheelPixels(10000); TestEqual(TEXT("Outdoor far limit"), Camera.Distance, 1400.0);
    Camera.WheelPixels(-500); Camera.OrbitPixels(100, 25);
    const double Distance = Camera.Distance, Yaw = Camera.Yaw, Pitch = Camera.Pitch;
    Camera.SetIndoor(true);
    TestEqual(TEXT("Indoor entry distance"), Camera.Distance, 220.0);
    TestEqual(TEXT("Indoor yaw reset"), Camera.Yaw, 0.0);
    TestTrue(TEXT("Indoor pitch reset"), FMath::IsNearlyEqual(Camera.Pitch, -FMath::RadiansToDegrees(0.42)));
    Camera.WheelPixels(-10000); TestEqual(TEXT("Indoor near limit"), Camera.Distance, 165.0);
    Camera.WheelPixels(10000); TestEqual(TEXT("Indoor far limit"), Camera.Distance, 380.0);
    Camera.SetIndoor(true); TestEqual(TEXT("Repeated entry is idempotent"), Camera.Distance, 380.0);
    Camera.OrbitPixels(70, -50); Camera.SetIndoor(false);
    TestEqual(TEXT("Outdoor zoom restored"), Camera.Distance, Distance);
    TestEqual(TEXT("Outdoor yaw restored"), Camera.Yaw, Yaw);
    TestEqual(TEXT("Outdoor pitch restored"), Camera.Pitch, Pitch);
    Camera.SetIndoor(false); TestEqual(TEXT("Repeated exit is idempotent"), Camera.Yaw, Yaw);
    FWarCameraState Normal, Inverted;
    Inverted.SetPreferences(1, 1, true, true);
    Normal.OrbitPixels(100, 20); Inverted.OrbitPixels(100, 20);
    TestTrue(TEXT("Horizontal inversion"), FMath::IsNearlyEqual(Normal.Yaw, -Inverted.Yaw));
    TestTrue(TEXT("Vertical inversion"), FMath::IsNearlyEqual(Normal.Pitch + Inverted.Pitch, -2.0 * FMath::RadiansToDegrees(0.45)));
    Camera.OrbitPixels(0, 10000);
    const double Limit = FMath::RadiansToDegrees(PI / 2.0 - 0.01);
    TestTrue(TEXT("Pitch upper limit"), FMath::IsNearlyEqual(Camera.Pitch, Limit));
    Camera.OrbitPixels(0, -10000); TestTrue(TEXT("Pitch lower limit"), FMath::IsNearlyEqual(Camera.Pitch, -Limit));
    Camera.SetPreferences(100, -1, false, false);
    TestEqual(TEXT("Look preference clamped"), Camera.LookSensitivity, 3.0);
    TestEqual(TEXT("Zoom preference clamped"), Camera.ZoomSensitivity, 0.25);
    Camera.WheelPixels(100); TestEqual(TEXT("Zoom sensitivity applied"), Camera.Distance, Distance + 25.0);
    const auto Saved = Camera;
    Camera.WheelPixels(std::numeric_limits<double>::infinity());
    Camera.OrbitPixels(std::numeric_limits<double>::quiet_NaN(), 10);
    TestEqual(TEXT("Invalid wheel leaves zoom intact"), Camera.Distance, Saved.Distance);
    TestEqual(TEXT("Invalid orbit leaves yaw intact"), Camera.Yaw, Saved.Yaw);
    TestEqual(TEXT("Invalid orbit leaves pitch intact"), Camera.Pitch, Saved.Pitch);
    Camera.SetPreferences(std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity(), false, false);
    TestEqual(TEXT("Invalid look uses default"), Camera.LookSensitivity, 1.0);
    TestEqual(TEXT("Invalid zoom uses default"), Camera.ZoomSensitivity, 1.0);
    return true;
}
#endif
