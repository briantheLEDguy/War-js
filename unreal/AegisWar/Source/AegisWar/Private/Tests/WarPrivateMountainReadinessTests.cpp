#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "../WarCitadelLightingWitness.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarPrivateMountainDiscovery,"AegisWar.Foundation.CitadelPrivateMountainDiscovery",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarPrivateMountainDiscovery::RunTest(const FString&)
{
    const FString Root=TEXT("/Game/WorldRebuild/AegisCitadel_abcdef123456");
    const FString Instance=Root+TEXT("/Materials/MI_PrivateSurface_mountain.MI_PrivateSurface_mountain");
    TestTrue(TEXT("Exact private MI discovered"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(Instance));
    TestTrue(TEXT("Existing material discovery retained"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(Root+TEXT("/Materials/M_PrivateSurface_stone.M_PrivateSurface_stone")));
    for (const auto& Bad:TArray<FString>{Instance+TEXT("_extra"),Instance.Replace(TEXT("abcdef123456"),TEXT("ABCDEF123456")),
        Instance.Replace(TEXT("abcdef123456"),TEXT("abcdef12345")),Instance.Replace(TEXT("AegisCitadel_"),TEXT("Other_")),
        TEXT("/Game/Capitals/crownward/MI_Mountain.MI_Mountain"),Instance.Replace(TEXT(".MI_PrivateSurface_mountain"),TEXT(".Other"))})
        TestFalse(TEXT("Unowned or ambiguous MI rejected"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(Bad));
    return true;
}
#endif
