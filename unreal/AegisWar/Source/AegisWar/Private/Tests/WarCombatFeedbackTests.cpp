#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCombatFeedback.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatFeedbackTest, "AegisWar.Foundation.CombatFeedback",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCombatFeedbackTest::RunTest(const FString& Parameters)
{
    TArray<FWarCombatNotice> Notices; uint32 Serial = 0;
    TestTrue(TEXT("Confirmed effective healing displayed"), WarCombatFeedback::Append(Notices, Serial, 1, TEXT("Heal"), TEXT("Ally"), 25, 10));
    TestFalse(TEXT("Duplicate cannot display twice"), WarCombatFeedback::Append(Notices, Serial, 1, TEXT("Heal"), TEXT("Ally"), 25, 10));
    TestFalse(TEXT("Overheal has no effective-heal message"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Heal"), TEXT("Ally"), 0, 10));
    TestFalse(TEXT("Invented event kinds rejected"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Victory"), TEXT("Ally"), 1, 10));
    TestFalse(TEXT("Negative damage rejected"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Hit"), TEXT("Enemy"), -1, 10));
    TestTrue(TEXT("Interruption needs no damage"), WarCombatFeedback::Append(Notices, Serial, 3, TEXT("Interrupt"), TEXT("Enemy"), 0, 10));
    TestFalse(TEXT("Out-of-order packet cannot revive feedback"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Hit"), TEXT("Enemy"), 1, 10));
    for (uint32 I = 4; I < 40; ++I) WarCombatFeedback::Append(Notices, Serial, I, TEXT("Hit"), TEXT("Enemy"), 1, 10);
    TestEqual(TEXT("Bounded on-screen messages"), Notices.Num(), 6);
    WarCombatFeedback::Append(Notices, Serial, 40, TEXT("Guarded"), TEXT("Enemy"), 10, 14);
    TestEqual(TEXT("Expired messages discarded"), Notices.Num(), 1);
    return true;
}
#endif
