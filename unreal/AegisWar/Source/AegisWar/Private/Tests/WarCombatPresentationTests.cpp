#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCombatPresentation.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatPresentationTest,"AegisWar.Foundation.CombatPresentationTiming",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCombatPresentationTest::RunTest(const FString& Parameters)
{
    using namespace WarCombatPresentation;
    TestTrue(TEXT("Release inside authored trail"),ValidTiming(1.25f,.57f,.39f,.71f));
    TestFalse(TEXT("No release outside clip"),ValidTiming(1,.8f,.9f,1.1f));
    TestFalse(TEXT("No negative trail"),ValidTiming(1,.5f,-.1f,.7f));
    TestEqual(TEXT("No early flash"),Afterglow(.49f,.5f,.6f),0.f);
    TestEqual(TEXT("Exact release flash"),Afterglow(.5f,.5f,.6f),1.f);
    TestEqual(TEXT("Spent flash is gone"),Afterglow(1.2f,.5f,.6f),0.f);
    TestEqual(TEXT("No charge before action"),Charge(-.1f,.5f),0.f);
    TestEqual(TEXT("Charge ends on release"),Charge(.5f,.5f),0.f);
    TestTrue(TEXT("Anticipation builds"),Charge(.4f,.5f)>Charge(.2f,.5f));
    return true;
}
#endif
