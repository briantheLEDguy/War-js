#include "Misc/AutomationTest.h"
#include "WarDevelopmentAccount.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarDevelopmentAccountTest, "AegisWar.Foundation.DevelopmentLoginBoundary",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarDevelopmentAccountTest::RunTest(const FString& Parameters)
{
    TestTrue(TEXT("Only the pinned development Auth endpoint launches"), UWarDevelopmentAccount::IsAllowedLoginUrl(
        TEXT("https://mfwnnvnvchwureeckdfx.supabase.co/auth/v1/authorize?provider=github")));
    TestFalse(TEXT("Reject unrelated providers"), UWarDevelopmentAccount::IsAllowedLoginUrl(TEXT("https://example.com/auth/v1/authorize?")));
    TestFalse(TEXT("Reject user-info hostname spoofing"), UWarDevelopmentAccount::IsAllowedLoginUrl(
        TEXT("https://mfwnnvnvchwureeckdfx.supabase.co@evil.example/auth/v1/authorize?")));
    TestFalse(TEXT("Reject insecure HTTP"), UWarDevelopmentAccount::IsAllowedLoginUrl(
        TEXT("http://mfwnnvnvchwureeckdfx.supabase.co/auth/v1/authorize?")));
    return true;
}
#endif
