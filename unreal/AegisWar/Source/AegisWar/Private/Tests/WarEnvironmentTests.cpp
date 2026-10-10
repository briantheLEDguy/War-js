#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarEnvironmentState.h"
#include "WarZoneLightingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarPracticalLight.h"
#include "WarInteriorAtmosphere.h"
#include "Components/BoxComponent.h"
#include "Components/PostProcessComponent.h"
#include "Engine/World.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Components/SkyLightComponent.h"
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
    auto* AuthoredSun=World->SpawnActor<ADirectionalLight>();
    AuthoredSun->GetLightComponent()->SetIntensity(12700.f);
    const auto SkyIntensity=[World]() {
        for(TActorIterator<ASkyLight> It(World);It;++It)
            if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment")))return It->GetLightComponent()->Intensity;
        return -1.f;
    };
    const auto ExposureBias=[World]() {
        for(TActorIterator<AActor> It(World);It;++It)
            if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment")))
                if(const auto* Component=It->FindComponentByClass<UPostProcessComponent>())return Component->Settings.AutoExposureBias;
        return -100.f;
    };
    const auto GroundMoon=[World]() -> ADirectionalLight* {
        for(TActorIterator<ADirectionalLight> It(World);It;++It)
            if(It->ActorHasTag(TEXT("WarGroundMoonlight")))return *It;
        return nullptr;
    };
    auto* Practical=World->SpawnActor<AWarPracticalLight>();Practical->ZoneId=TEXT("sunmeadow_march");
    TestTrue(TEXT("Night preview available"),UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,2700,.8f));
    TestEqual(TEXT("Fixture illuminates night"),Practical->GetLightComponent()->Intensity,900.f);
    TestEqual(TEXT("Moonlit sky fill remains restrained"),SkyIntensity(),.18f);
    TestEqual(TEXT("Farmland night retains readable ground exposure"),ExposureBias(),3.25f);
    auto* Moon=GroundMoon();
    if(!TestNotNull(TEXT("Separate ground moonlight"),Moon)){World->DestroyWorld(false);return false;}
    const auto* MoonComponent=CastChecked<UDirectionalLightComponent>(Moon->GetLightComponent());
    TestFalse(TEXT("Moon cannot brighten the atmospheric sky"),MoonComponent->bAtmosphereSunLight);
    TestTrue(TEXT("Moon retains terrain and building shadows"),MoonComponent->CastShadows);
    TestTrue(TEXT("Moon stays visible under stronger cosmetic weather"),MoonComponent->IsVisible());
    TestTrue(TEXT("Weather gently softens ground moonlight"),FMath::IsNearlyEqual(MoonComponent->Intensity,520.f));
    TestTrue(TEXT("Moon angle reveals broad terrain relief"),FMath::IsNearlyEqual(Moon->GetActorRotation().Pitch,-42.f));
    TestEqual(TEXT("Soft moon shadow source"),MoonComponent->LightSourceAngle,1.2f);
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,2700,0);
    TestEqual(TEXT("Clear night ground output"),MoonComponent->Intensity,650.f);
    const auto NightMoonRotation=Moon->GetActorRotation();
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,3599.99,0);
    TestTrue(TEXT("Moon keeps its direction at the end of night"),Moon->GetActorRotation().Equals(NightMoonRotation,.001f));
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,3600,0);
    TestTrue(TEXT("Hourly wrap cannot snap moon shadows"),Moon->GetActorRotation().Equals(NightMoonRotation,.001f));
    TestEqual(TEXT("Ground output stays continuous at dawn start"),MoonComponent->Intensity,650.f);


    TestFalse(TEXT("Regional rig hides authored sun temporarily"),AuthoredSun->GetLightComponent()->IsVisible());
    float Night=0,Day=0;
    for(TActorIterator<ADirectionalLight> It(World);It;++It)if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment"))&&CastChecked<UDirectionalLightComponent>(It->GetLightComponent())->bAtmosphereSunLight)Night=It->GetLightComponent()->Intensity;
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,1200,0);
    TestEqual(TEXT("Fixture extinguishes in daylight"),Practical->GetLightComponent()->Intensity,0.f);
    TestEqual(TEXT("Daylight receives no additional moon output"),MoonComponent->Intensity,0.f);
    TestFalse(TEXT("Daylight disables moon rendering"),MoonComponent->IsVisible());
    for(TActorIterator<ADirectionalLight> It(World);It;++It)if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment"))&&CastChecked<UDirectionalLightComponent>(It->GetLightComponent())->bAtmosphereSunLight)Day=It->GetLightComponent()->Intensity;
    TestTrue(TEXT("Night stays darker with readable moonlight"),Night>0&&Night<Day*.1f);
    TestEqual(TEXT("Farmland daylight avoids excessive direct contrast"),Day,14000.f);
    TestEqual(TEXT("Farmland sky fills canopy shadows"),SkyIntensity(),4.f);
    TestEqual(TEXT("Night readability preserves daylight exposure"),ExposureBias(),-.5f);
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,2250,0);
    TestEqual(TEXT("Night readability blends continuously through dusk"),ExposureBias(),1.375f);
    TestEqual(TEXT("Ground moon fades continuously through dusk"),MoonComponent->Intensity,325.f);
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("cinderfen_outskirts"),FVector::ZeroVector,1200,0);
    float FenDay=0,FenNight=0;
    for(TActorIterator<ADirectionalLight> It(World);It;++It)if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment"))&&CastChecked<UDirectionalLightComponent>(It->GetLightComponent())->bAtmosphereSunLight)FenDay=It->GetLightComponent()->Intensity;
    TestTrue(TEXT("Fen daytime lights the dark substrate"),FenDay>=20000.f);
    TestEqual(TEXT("Fen retains regional ambient output"),SkyIntensity(),10500.f/8000.f);
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("cinderfen_outskirts"),FVector::ZeroVector,2700,0);
    for(TActorIterator<ADirectionalLight> It(World);It;++It)if(It->ActorHasTag(TEXT("WarLocalZoneEnvironment"))&&CastChecked<UDirectionalLightComponent>(It->GetLightComponent())->bAtmosphereSunLight)FenNight=It->GetLightComponent()->Intensity;
    TestEqual(TEXT("Fen readability change preserves moon output"),FenNight,500.f);
    TestTrue(TEXT("Fen night retains its regional exposure offset"),FMath::IsNearlyEqual(ExposureBias(),4.15f));
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("brightfen_approach"),FVector::ZeroVector,2700,0);
    TestEqual(TEXT("Later batch retains its previous night exposure"),ExposureBias(),UWarZoneLightingSubsystem::FindProfile(TEXT("brightfen_approach"))->ExposureBias+2.25f);
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,1200,0);
    Practical->DayLumens=250;Practical->NightLumens=700;
    Practical->ApplyTime(1200);TestEqual(TEXT("Interior fixture retains daylight illumination"),Practical->GetLightComponent()->Intensity,250.f);
    Practical->ApplyTime(2700);TestEqual(TEXT("Interior fixture follows night level"),Practical->GetLightComponent()->Intensity,700.f);
    Practical->ApplyTime(2250);TestEqual(TEXT("Interior fixture blends at dusk"),Practical->GetLightComponent()->Intensity,362.5f);
    Practical->DayLumens=-10;Practical->ApplyTime(1200);TestEqual(TEXT("Invalid fixture output is clamped"),Practical->GetLightComponent()->Intensity,0.f);
    auto* Interior=World->SpawnActor<AWarInteriorAtmosphere>();Interior->ZoneId=TEXT("sunmeadow_march");
    TestFalse(TEXT("Room exposure is bounded"),Interior->Exposure->bUnbound);
    TestEqual(TEXT("Room geometry does not block movement"),Interior->RoomBounds->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
    TestEqual(TEXT("Day eye adaptation"),Interior->Exposure->Settings.AutoExposureBias,2.f);
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("sunmeadow_march"),FVector::ZeroVector,2700,0);
    TestEqual(TEXT("Room follows night preview"),Interior->Exposure->Settings.AutoExposureBias,3.5f);
    Interior->ApplyTime(2250);TestEqual(TEXT("Room blends at dusk"),Interior->Exposure->Settings.AutoExposureBias,2.75f);
    UWarZoneLightingSubsystem::PreviewEnvironment(World,TEXT("greybrook_crossing"),FVector::ZeroVector,1200,0);
    TestEqual(TEXT("Untouched daylight retains its fill-derived sky"),SkyIntensity(),10500.f/8000.f);
    TestFalse(TEXT("Leaving T1 disables ground moonlight"),MoonComponent->IsVisible());
    TestEqual(TEXT("Leaving T1 clears ground moon output"),MoonComponent->Intensity,0.f);
    TestTrue(TEXT("Accepted capital preview remains available"),UWarZoneLightingSubsystem::PreviewWorld(World,TEXT("aegis_capital"),FVector::ZeroVector));
    TestTrue(TEXT("Capital restores authored sun visibility"),AuthoredSun->GetLightComponent()->IsVisible());
    TestFalse(TEXT("Capital receives no ground moonlight"),MoonComponent->IsVisible());
    TestEqual(TEXT("Capital restores authored sun output"),AuthoredSun->GetLightComponent()->Intensity,12700.f);
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
