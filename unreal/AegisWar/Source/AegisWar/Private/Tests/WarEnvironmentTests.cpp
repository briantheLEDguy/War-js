#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarEnvironmentState.h"
#include "WarZoneLightingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarPracticalLight.h"
#include "Engine/World.h"
#include "Engine/DirectionalLight.h"
#include "Components/DirectionalLightComponent.h"
#include "EngineUtils.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarEnvironmentCycleTest,"AegisWar.Foundation.RegionalEnvironment",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarEnvironmentCycleTest::RunTest(const FString& Parameters)
{
    TestEqual(TEXT("Hour wraps"),AWarEnvironmentState::CycleSeconds(3600),0.);
    TestEqual(TEXT("Negative epoch wraps"),AWarEnvironmentState::CycleSeconds(-1),3599.);
    TestEqual(TEXT("Dawn midpoint"),AWarEnvironmentState::Daylight(150),.5f);
    TestEqual(TEXT("Thirty minute day ends at 2100"),AWarEnvironmentState::Daylight(2100),1.f);
    TestEqual(TEXT("Dusk midpoint"),AWarEnvironmentState::Daylight(2250),.5f);
    TestEqual(TEXT("Twenty minute night starts at 2400"),AWarEnvironmentState::Daylight(2400),0.f);
    TestFalse(TEXT("Capital retains authored cycle"),AWarEnvironmentState::IsDynamicZone(TEXT("aegis_capital")));
    int32 Strong=0;
    for(int64 Interval=0;Interval<1000;Interval++)
    {
        const float W=AWarEnvironmentState::WeatherAt(TEXT("sunmeadow_march"),Interval);
        TestEqual(TEXT("Weather is reproducible"),W,AWarEnvironmentState::WeatherAt(TEXT("sunmeadow_march"),Interval));
        if(W>.5f)++Strong;
    }
    TestTrue(TEXT("Strong conditions are occasional"),Strong>20&&Strong<200);
    const auto Values=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    if(!TestNotNull(TEXT("Preview world"),World))return false;
    auto* Practical=World->SpawnActor<AWarPracticalLight>();Practical->ZoneId=TEXT("sunmeadow_march");
    TestTrue(TEXT("Night preview available"),UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,2700,.8f));
    TestEqual(TEXT("Fixture illuminates night"),Practical->GetLightComponent()->Intensity,900.f);
    float Night=0,Day=0;
    for(TActorIterator<ADirectionalLight> It(World);It;++It)if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment"))&&CastChecked<UDirectionalLightComponent>(It->GetLightComponent())->bAtmosphereSunLight)Night=It->GetLightComponent()->Intensity;
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,1200,0);
    TestEqual(TEXT("Fixture extinguishes in daylight"),Practical->GetLightComponent()->Intensity,0.f);
    for(TActorIterator<ADirectionalLight> It(World);It;++It)if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment"))&&CastChecked<UDirectionalLightComponent>(It->GetLightComponent())->bAtmosphereSunLight)Day=It->GetLightComponent()->Intensity;
    TestTrue(TEXT("Night stays darker with readable moonlight"),Night>0&&Night<Day*.1f);
    World->DestroyWorld(false);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSpatialOutlineTest,"AegisWar.Foundation.SpatialOutline",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSpatialOutlineTest::RunTest(const FString& Parameters)
{
    const auto Values=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    if(!TestNotNull(TEXT("Spatial preview world"),World))return false;
    auto* Anchor=World->SpawnActor<AWarZoneAnchor>();
    Anchor->bUseSpatialBounds=true;Anchor->ContentMin=FVector2D(-1000,-500);Anchor->ContentMax=FVector2D(1000,500);
    Anchor->PlayableOutline={FVector2D(-800,-400),FVector2D(800,-400),FVector2D(800,400),FVector2D(100,400),FVector2D(100,0),FVector2D(-100,0),FVector2D(-100,400),FVector2D(-800,400)};
    TestTrue(TEXT("Backdrop retains ownership"),Anchor->ContainsOwnedPoint(FVector(0,300,0)));
    TestFalse(TEXT("Concave recess excludes movement"),Anchor->ContainsPlayablePoint(FVector(0,300,0)));
    TestFalse(TEXT("Valid endpoints cannot cross a concave recess"),Anchor->ContainsPlayableSegment(FVector(-400,200,0),FVector(400,200,0),40));
    TestTrue(TEXT("Connected corridor remains traversable"),Anchor->ContainsPlayableSegment(FVector(-400,-200,0),FVector(400,-200,0),40));
    TestTrue(TEXT("Connected ground admitted"),Anchor->ContainsPlayablePoint(FVector(-400,200,0),40));
    TestFalse(TEXT("Full capsule clearance required"),Anchor->ContainsPlayablePoint(FVector(-120,200,0),40));
    TestFalse(TEXT("Rectangular extent enforced"),Anchor->ContainsOwnedPoint(FVector(0,600,0)));
    Anchor->bUseSpatialBounds=false;Anchor->HalfSize=1000;
    TestTrue(TEXT("Legacy square is retained"),Anchor->ContainsPlayablePoint(FVector(0,600,0)));
    World->DestroyWorld(false);return true;
}
#endif
