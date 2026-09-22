#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarZonePortal.h"
#include "WarZoneAnchor.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarGameMode.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/Brush.h"
#include "Engine/BlockingVolume.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarZoneStreamingTest, "AegisWar.Foundation.ZoneStreaming",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarZoneStreamingTest::RunTest(const FString& Parameters)
{
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Editor, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Builder brush fixture world"), World)) return false;
    const auto CheckCollision = &UWarZoneStreamingSubsystem::RequiresActorCollisionReadiness;
    auto* Builder = World->GetDefaultBrush();
    TestNotNull(TEXT("Unreal creates the level's builder brush"), Builder);
    TestFalse(TEXT("Builder brush cannot block entry forever"), CheckCollision(Builder));
    auto* Wall = World->SpawnActor<ABlockingVolume>();
    TestTrue(TEXT("Real blocking brushes still require collision"), CheckCollision(Wall));
    Wall->SetActorEnableCollision(false);
    TestFalse(TEXT("Disabled blockers do not delay entry"), CheckCollision(Wall));
    TestFalse(TEXT("Missing actors are ignored"), CheckCollision(nullptr));
    World->DestroyWorld(false);
    const auto Continue = &UWarZoneStreamingSubsystem::CanContinue;
    TestTrue(TEXT("Loading retains a live player inside the source portal"), Continue(true,true,true,900,900,29,30));
    TestFalse(TEXT("Walking away cancels deferred travel"), Continue(true,true,true,901,900,1,30));
    TestFalse(TEXT("Death cancels deferred travel"), Continue(true,false,true,0,900,1,30));
    TestFalse(TEXT("A replacement pawn cannot inherit a pending teleport"), Continue(false,true,true,0,900,1,30));
    TestFalse(TEXT("Lost visual readiness cancels travel"), Continue(true,true,false,0,900,1,30));
    TestFalse(TEXT("The loading deadline does not extend on retries"), Continue(true,true,true,0,900,30,30));
    TestFalse(TEXT("Invalid distance cancels travel"), Continue(true,true,true,std::numeric_limits<double>::quiet_NaN(),900,1,30));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarZonePortalTest, "AegisWar.Foundation.ZonePortal",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarZonePortalTest::RunTest(const FString& Parameters)
{
    const auto Enter = &AWarZonePortal::CanEnter;
    TestEqual(TEXT("Flat landing retains five centimetres of clearance"), AWarZonePortal::CapsuleGroundOffset(96,42,1), 101.0);
    const double Offset = AWarZonePortal::CapsuleGroundOffset(96,42,0.8);
    TestTrue(TEXT("Capsule hemisphere clears a sloping plane"), (Offset - (96-42)) * 0.8 > 42);
    TestTrue(TEXT("Live development player may enter at radius and cooldown boundaries"), Enter(true,true,true,true,true,900,900,3,3));
    TestFalse(TEXT("Clients cannot travel themselves"), Enter(false,true,true,true,true,0,900,3,0));
    TestFalse(TEXT("Production remains closed"), Enter(true,false,true,true,true,0,900,3,0));
    TestFalse(TEXT("Dead characters cannot travel"), Enter(true,true,false,true,true,0,900,3,0));
    TestFalse(TEXT("Missing visuals cannot travel"), Enter(true,true,true,false,true,0,900,3,0));
    TestFalse(TEXT("Unbuilt destinations stay closed"), Enter(true,true,true,true,false,0,900,3,0));
    TestFalse(TEXT("Remote activation rejected"), Enter(true,true,true,true,true,901,900,3,0));
    TestFalse(TEXT("Immediate return prevented"), Enter(true,true,true,true,true,0,900,2.99,3));
    TestFalse(TEXT("Invalid location rejected"), Enter(true,true,true,true,true,std::numeric_limits<double>::quiet_NaN(),900,3,0));
    TestTrue(TEXT("Zone bounds include the authored boundary at any floor"), AWarZoneAnchor::ContainsPoint(FVector(200000,0,0),60000,FVector(260000,-60000,-5000)));
    TestFalse(TEXT("Neighbouring zones do not leak into the local map"), AWarZoneAnchor::ContainsPoint(FVector(200000,0,0),60000,FVector(260001,0,0)));
    TestFalse(TEXT("Invalid zone extent rejected"), AWarZoneAnchor::ContainsPoint(FVector::ZeroVector,-1,FVector::ZeroVector));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarZoneRespawnTest, "AegisWar.Foundation.ZoneRespawn",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarZoneRespawnTest::RunTest(const FString& Parameters)
{
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Respawn test world"), World)) return false;
    auto& Context = GEngine->CreateNewWorldContext(EWorldType::Game); Context.SetCurrentWorld(World);
    auto* Mode = World->SpawnActor<AWarGameMode>();
    auto* Player = World->SpawnActor<AWarPlayerController>();
    auto* State = World->SpawnActor<AWarPlayerState>();
    Player->SetPlayerState(State);
    auto* Capital = World->SpawnActor<AWarZoneAnchor>(); Capital->ZoneId = TEXT("aegis_capital");
    auto* Riftspire = World->SpawnActor<AWarZoneAnchor>(); Riftspire->ZoneId = TEXT("riftspire_capital");
    auto* Field = World->SpawnActor<AWarZoneAnchor>(); Field->ZoneId = TEXT("sunmeadow_march");
    Player->StartSpot = Capital;
    State->SetCurrentZoneTrusted(Capital->ZoneId);
    State->SetDevelopmentRealm(EWarRealm::Riftbound);
    TestEqual(TEXT("First realm assignment replaces a provisional login zone"), State->GetCurrentZone(), Riftspire->ZoneId);
    TestTrue(TEXT("Riftbound starts use Riftspire after engine login"), Mode->FindPlayerStart_Implementation(Player, FString()) == Riftspire);
    State->SetCurrentZoneTrusted(Field->ZoneId);
    State->SetDevelopmentRealm(EWarRealm::Aegis);
    TestEqual(TEXT("Repeated realm assignment cannot reset travel or identity"), State->GetCurrentZone(), Field->ZoneId);
    TestEqual(TEXT("Realm remains server assigned"), State->GetRealm(), EWarRealm::Riftbound);
    TestFalse(TEXT("Travel invalidates the original capital start"), Mode->ShouldSpawnAtStartSpot(Player));
    TestTrue(TEXT("Engine start lookup selects the current zone"), Mode->FindPlayerStart_Implementation(Player, FString()) == Field);
    State->SetCurrentZoneTrusted(TEXT("legacy_map"));
    TestTrue(TEXT("Maps without zone anchors retain engine start behaviour"), Mode->ShouldSpawnAtStartSpot(Player));
    World->DestroyWorld(false); GEngine->DestroyWorldContext(World);
    return true;
}
#endif
