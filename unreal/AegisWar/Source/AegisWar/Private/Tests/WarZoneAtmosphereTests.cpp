#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarZoneLightingSubsystem.h"
#include "Engine/World.h"
#include "Engine/DirectionalLight.h"
#include "Components/DirectionalLightComponent.h"
#include "EngineUtils.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarZoneAtmosphereTest, "AegisWar.Foundation.ZoneAtmosphere",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarZoneAtmosphereTest::RunTest(const FString& Parameters)
{
    TSet<FName> Zones; TSet<FString> Looks;
    for (const auto& P : UWarZoneLightingSubsystem::Profiles())
    {
        TestFalse(TEXT("Every zone occurs once"), Zones.Contains(P.Zone)); Zones.Add(P.Zone);
        const FString Signature = P.SunRotation.ToString() + P.SunColor.ToString() + P.FillColor.ToString();
        TestFalse(TEXT("Zone lighting signatures differ"), Looks.Contains(Signature)); Looks.Add(Signature);
        TestTrue(TEXT("Readable fill and finite art controls"), P.FillLux > 0 && P.SunLux > P.FillLux
            && P.FogDensity >= 0 && P.FogDensity < .05 && P.ShadowGamma >= 1 && !P.SunRotation.ContainsNaN());
    }
    TestEqual(TEXT("All campaign zones have lighting"), Zones.Num(), 32);
    TestNull(TEXT("Unknown zone does not borrow a theme"), UWarZoneLightingSubsystem::FindProfile(TEXT("missing")));
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::EditorPreview, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Lighting test world"), World)) return false;
    auto* Authored = World->SpawnActor<ADirectionalLight>();
    Authored->GetLightComponent()->SetIntensity(1234);
    auto* Lighting = World->GetSubsystem<UWarZoneLightingSubsystem>();
    if (!TestNotNull(TEXT("Local atmosphere subsystem"), Lighting)) { World->DestroyWorld(false); return false; }
    TestTrue(TEXT("Marsh preview"), Lighting->PreviewZone(TEXT("cinderfen_outskirts"), FVector(200000, 0, 0)));
    TestFalse(TEXT("Authored sun temporarily hidden"), Authored->GetLightComponent()->IsVisible());
    TestTrue(TEXT("Farmland preview reuses environment"), Lighting->PreviewZone(TEXT("sunmeadow_march"), FVector(400000, 0, 0)));
    int32 TransientActors = 0;
    for (TActorIterator<AActor> It(World); It; ++It) if (It->ActorHasTag(TEXT("WarLocalZoneEnvironment")))
    {
        ++TransientActors; TestTrue(TEXT("Lighting cannot alter saved map packages"), It->HasAnyFlags(RF_Transient));
        TestFalse(TEXT("Local lighting is never replicated"), It->GetIsReplicated());
        if (const auto* Light = Cast<ADirectionalLight>(*It))
        {
            const auto* Component = CastChecked<UDirectionalLightComponent>(Light->GetLightComponent());
            TestEqual(TEXT("Primary sun wins forward shading over fill"), Component->ForwardShadingPriority,
                Component->bAtmosphereSunLight ? 1 : 0);
        }
    }
    TestEqual(TEXT("Only one environment is resident across transitions"), TransientActors, 6);
    TestFalse(TEXT("Unknown preview is recoverable"), Lighting->PreviewZone(TEXT("missing"), FVector::ZeroVector));
    TestEqual(TEXT("Failed preview keeps previous environment"), Lighting->GetActiveZone(), FName(TEXT("sunmeadow_march")));
    TestTrue(TEXT("Capital restores authored lighting"), Lighting->PreviewZone(TEXT("aegis_capital"), FVector::ZeroVector));
    TestTrue(TEXT("Original visibility restored"), Authored->GetLightComponent()->IsVisible());
    TestEqual(TEXT("Original light intensity unchanged"), Authored->GetLightComponent()->Intensity, 1234.f);
    World->DestroyWorld(false);
    return true;
}
#endif
