#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarInterfaceRules.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarInterfaceTest, "AegisWar.Foundation.InterfaceRules",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarInterfaceTest::RunTest(const FString& Parameters)
{
    const FVector Centre(1200, -800, 200);
    const FVector2D Size(600, 400);
    TestEqual(TEXT("Player stays centred"), WarInterface::MapPoint(Centre, Centre, 1000, Size), Size * 0.5);
    TestEqual(TEXT("North is top edge"), WarInterface::MapPoint(Centre + FVector(1000, 0, 0), Centre, 1000, Size), FVector2D(300, 0));
    TestEqual(TEXT("East is right edge"), WarInterface::MapPoint(Centre + FVector(0, 1000, 0), Centre, 1000, Size), FVector2D(600, 200));
    TestEqual(TEXT("Height does not shift map"), WarInterface::MapPoint(Centre + FVector(0, 0, 500), Centre, 1000, Size), Size * 0.5);
    TestEqual(TEXT("Zero radius safe"), WarInterface::MapPoint(Centre, Centre, 0, Size), Size * 0.5);
    TestEqual(TEXT("Invalid radius safe"), WarInterface::MapPoint(Centre, Centre, std::numeric_limits<double>::infinity(), Size), Size * 0.5);
    TestTrue(TEXT("Distant landmarks stay outside, not clamped onto edge"), WarInterface::MapPoint(Centre + FVector(0, 2000, 0), Centre, 1000, Size).X > Size.X);
    TestEqual(TEXT("Zoom expands visible area"), WarInterface::MapPoint(Centre + FVector(0, 1000, 0), Centre, 2000, Size), FVector2D(450, 200));
    TestEqual(TEXT("Frame limit minimum"), WarInterface::SafeFrameLimit(0), 30.f);
    TestEqual(TEXT("Frame limit maximum"), WarInterface::SafeFrameLimit(500), 240.f);
    TestEqual(TEXT("Frame limit NaN"), WarInterface::SafeFrameLimit(std::numeric_limits<float>::quiet_NaN()), 60.f);
    return true;
}
#endif
