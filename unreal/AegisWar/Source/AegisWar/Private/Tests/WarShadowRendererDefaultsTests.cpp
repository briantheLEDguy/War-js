#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/ConfigCacheIni.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarShadowRendererDefaultsTest,"AegisWar.Foundation.ShadowRendererDefaults",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarShadowRendererDefaultsTest::RunTest(const FString& Parameters)
{
    int32 ConfiguredMode=0;
    TestTrue(TEXT("Normal engine configuration supplies a shadow renderer"),GConfig && GConfig->GetInt(
        TEXT("/Script/Engine.RendererSettings"),TEXT("r.Shadow.Virtual.Enable"),ConfiguredMode,GEngineIni));
    TestEqual(TEXT("Normal startup uses virtual shadow maps"),ConfiguredMode,1);
    const auto* Mode=IConsoleManager::Get().FindConsoleVariable(TEXT("r.Shadow.Virtual.Enable"));
    if (!TestNotNull(TEXT("The installed engine exposes virtual shadow maps"),Mode)) return false;
    TestEqual(TEXT("Startup applies the configured renderer without a diagnostic override"),Mode->GetInt(),ConfiguredMode);
    const auto* Lights=IConsoleManager::Get().FindConsoleVariable(TEXT("r.Shadow.Virtual.OnePassProjection.MaxLightsPerPixel"));
    if (TestNotNull(TEXT("The installed renderer exposes packed shadow-light capacity"),Lights))
        TestEqual(TEXT("Ordinary startup preserves full filtering for dense practical lights"),Lights->GetInt(),32);
    int32 HighQualityPages=0;
    TestTrue(TEXT("High-quality shadows have a bounded page pool"),GConfig->GetInt(
        TEXT("ShadowQuality@3"),TEXT("r.Shadow.Virtual.MaxPhysicalPages"),HighQualityPages,GScalabilityIni));
    TestEqual(TEXT("High quality provides headroom for the measured pool overflow"),HighQualityPages,8192);
    int32 LowQualityPages=0;
    TestTrue(TEXT("Low quality retains its inherited bounded pool"),GConfig->GetInt(
        TEXT("ShadowQuality@0"),TEXT("r.Shadow.Virtual.MaxPhysicalPages"),LowQualityPages,GScalabilityIni));
    TestTrue(TEXT("Low quality does not inherit the high-quality memory allocation"),LowQualityPages>0 && LowQualityPages<HighQualityPages);
    return true;
}
#endif
