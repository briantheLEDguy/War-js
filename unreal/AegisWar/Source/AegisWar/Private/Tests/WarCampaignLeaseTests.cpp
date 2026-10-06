#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarSiegeEncounter.h"
#include "Engine/World.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCampaignLeaseTest,"AegisWar.Foundation.CampaignLease",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCampaignLeaseTest::RunTest(const FString& Parameters)
{
    const auto Due=&UWarCampaignSiegeSubsystem::LeaseRequestDue;
    using Request=EWarCampaignLeaseRequest;
    TestTrue(TEXT("Healthy ownership leaves the request queue available"),Due(false,9,15,0)==Request::None);
    TestTrue(TEXT("Renew before the remaining five seconds are consumed by queued enrollment"),Due(false,10,15,0)==Request::Heartbeat);
    TestTrue(TEXT("Expired ownership reactivates before any queued mutation"),Due(false,15,15,0)==Request::Reactivate);
    TestTrue(TEXT("Paused ownership requires original-content reactivation"),Due(true,9,15,0)==Request::Reactivate);
    TestTrue(TEXT("Unavailable authority retries are bounded"),Due(true,9,15,11)==Request::None);
    TestTrue(TEXT("Nonfinite lease clocks cannot start a request"),Due(false,9,std::numeric_limits<double>::quiet_NaN(),0)==Request::None);
    const auto Values=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Editor,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    if (!TestNotNull(TEXT("Streaming ownership fixture"),World)) return false;
    auto* Capital=World->SpawnActor<AWarZoneAnchor>();Capital->ZoneId=TEXT("aegis_capital");
    auto* Other=World->SpawnActor<AWarZoneAnchor>();Other->ZoneId=TEXT("sunmeadow_march");
    auto* Streaming=NewObject<UWarZoneStreamingSubsystem>(World);
    auto* Bootstrap=NewObject<UWarCampaignSiegeSubsystem>(World);
    auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();
    auto* OtherOwner=World->SpawnActor<AActor>();
    Streaming->PinZone(Bootstrap,TEXT("aegis_capital"));
    Streaming->PinZone(Encounter,TEXT("aegis_capital"));
    Streaming->PinZone(OtherOwner,TEXT("sunmeadow_march"));
    TestEqual(TEXT("Bootstrap, encounter and unrelated-zone leases coexist"),Streaming->ZonePins.Num(),3);
    Streaming->ReleaseZone(Bootstrap);
    TestEqual(TEXT("Releasing bootstrap preserves both existing leases"),Streaming->ZonePins.Num(),2);
    TestTrue(TEXT("Encounter retains capital residency"),Streaming->ZonePins.FindRef(Encounter)==TEXT("aegis_capital"));
    TestTrue(TEXT("Unrelated zone retains residency"),Streaming->ZonePins.FindRef(OtherOwner)==TEXT("sunmeadow_march"));
    Streaming->PinZone(Bootstrap,TEXT("unknown_zone"));
    TestEqual(TEXT("An unknown destination cannot acquire a subsystem lease"),Streaming->ZonePins.Num(),2);
    World->DestroyWorld(false);
    return true;
}
#endif
