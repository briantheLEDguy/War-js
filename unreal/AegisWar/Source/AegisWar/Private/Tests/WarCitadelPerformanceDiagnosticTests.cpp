#include "Misc/AutomationTest.h"
#include "HAL/IConsoleManager.h"
#include "WarCitadelLumenStudyRuntime.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelPerformanceIsolationTest,
    "AegisWar.Foundation.CitadelPerformanceIsolation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCitadelPerformanceIsolationTest::RunTest(const FString&)
{
    TMap<FString,int32> Values;
    using WarCitadelLumenStudyRuntime::PerformanceRecipe;
    TestTrue(TEXT("ordinary baseline supported"),PerformanceRecipe(TEXT("baseline"),Values));
    TestTrue(TEXT("baseline changes no graphics"),Values.IsEmpty());
    TestTrue(TEXT("point-only isolation has an explicit mode"),PerformanceRecipe(TEXT("point_shadows_off"),Values));
    TestTrue(TEXT("point-only isolation changes no renderer startup gate"),Values.IsEmpty());
    const TPair<const TCHAR*,const TCHAR*> Modes[]={
        {TEXT("preview_shadows_off"),TEXT("r.Shadow.UnbuiltPreviewInGame")},
        {TEXT("shadows_off"),TEXT("r.ShadowQuality")},
        {TEXT("ssgi_off"),TEXT("r.SSGI.Quality")},
        {TEXT("reflections_off"),TEXT("r.SSR.Quality")}};
    for (const auto& Mode:Modes)
    {
        TestTrue(FString(TEXT("recognized isolation "))+Mode.Key,PerformanceRecipe(Mode.Key,Values));
        TestEqual(TEXT("one subsystem changes at a time"),Values.Num(),1);
        TestEqual(TEXT("isolation disables its subsystem"),Values.FindRef(Mode.Value),0);
        const auto* CVar=IConsoleManager::Get().FindConsoleVariable(Mode.Value);
        TestNotNull(FString(TEXT("installed engine exposes "))+Mode.Value,CVar);
        if (CVar) TestFalse(TEXT("never changes readonly startup gates"),(CVar->GetFlags() & ECVF_ReadOnly)!=0);
    }
    TestFalse(TEXT("arbitrary console commands rejected"),PerformanceRecipe(TEXT("r.AllowStaticLighting 0"),Values));
    TestTrue(TEXT("rejected requests clear stale overrides"),Values.IsEmpty());
    TestFalse(TEXT("art preset cannot masquerade as performance baseline"),PerformanceRecipe(TEXT("lumen_software"),Values));
    TestTrue(TEXT("bounded cache experiment supported"),PerformanceRecipe(TEXT("shadow_cache_512"),Values));
    TestEqual(TEXT("cache experiment changes only its memory budget"),Values.Num(),1);
    TestEqual(TEXT("512 MiB cache requested"),Values.FindRef(TEXT("r.Shadow.WholeSceneShadowCacheMb")),512);
    TestTrue(TEXT("larger bounded cache experiment supported"),PerformanceRecipe(TEXT("shadow_cache_1024"),Values));
    TestEqual(TEXT("1024 MiB cache requested"),Values.FindRef(TEXT("r.Shadow.WholeSceneShadowCacheMb")),1024);
    TestFalse(TEXT("unbounded cache requests rejected"),PerformanceRecipe(TEXT("shadow_cache_65536"),Values));
    TestTrue(TEXT("rejected cache request leaves no override"),Values.IsEmpty());
    TestTrue(TEXT("virtual-shadow diagnostic supported"),PerformanceRecipe(TEXT("virtual_shadow_maps"),Values));
    TestEqual(TEXT("virtual-shadow diagnostic changes one control"),Values.Num(),1);
    TestEqual(TEXT("virtual-shadow renderer requested"),Values.FindRef(TEXT("r.Shadow.Virtual.Enable")),1);
    return !HasAnyErrors();
}
#endif
