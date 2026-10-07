#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarZonePortal.h"
#include "WarZoneAnchor.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarGameMode.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarSiegeEncounter.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/Brush.h"
#include "Engine/BlockingVolume.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Components/SphereComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "LevelUtils.h"
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

    World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Connectionless streaming fixture world"), World)) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    // Runtime actor initialization registers controllers and enables the engine RPC dispatch path.
    World->InitializeActorsForPlay(FURL());
    TestTrue(TEXT("Streaming fixture has completed runtime actor initialization"), World->AreActorsInitialized());
    auto* Streaming = World->GetSubsystem<UWarZoneStreamingSubsystem>();
    auto* FirstPlayer = World->SpawnActor<AWarPlayerController>();
    auto* SecondPlayer = World->SpawnActor<AWarPlayerController>();
    auto* FirstState = World->SpawnActor<AWarPlayerState>();
    auto* SecondState = World->SpawnActor<AWarPlayerState>();
    auto* FirstZone = World->SpawnActor<AWarZoneAnchor>();
    auto* SecondZone = World->SpawnActor<AWarZoneAnchor>();
    if (!TestNotNull(TEXT("World streaming subsystem"), Streaming)
        || !TestNotNull(TEXT("First synthetic controller"), FirstPlayer)
        || !TestNotNull(TEXT("Second synthetic controller"), SecondPlayer)
        || !TestNotNull(TEXT("First controller state"), FirstState)
        || !TestNotNull(TEXT("Second controller state"), SecondState)
        || !TestNotNull(TEXT("First zone anchor"), FirstZone)
        || !TestNotNull(TEXT("Second zone anchor"), SecondZone))
    {
        World->DestroyWorld(false); GEngine->DestroyWorldContext(World);
        return false;
    }
    FirstPlayer->SetPlayerState(FirstState); SecondPlayer->SetPlayerState(SecondState);
    FirstZone->ZoneId = TEXT("sunmeadow_march"); SecondZone->ZoneId = TEXT("aegis_gate_fortress");
    FirstState->SetCurrentZoneTrusted(FirstZone->ZoneId); SecondState->SetCurrentZoneTrusted(SecondZone->ZoneId);
    const auto DeclareLevel = [World](AWarZoneAnchor* Anchor, FName Package)
    {
        auto* Level = NewObject<ULevelStreamingDynamic>(World);
        Level->SetWorldAssetByPackageName(Package);
        World->AddStreamingLevel(Level);
        Anchor->ContentLevels.Add(Package);
        return Level;
    };
    auto* FirstLevel = DeclareLevel(FirstZone, TEXT("/Game/Tests/Streaming/Sunmeadow"));
    auto* SecondLevel = DeclareLevel(SecondZone, TEXT("/Game/Tests/Streaming/AegisGate"));
    TestTrue(TEXT("Engine streaming status lookup resolves both declared levels"),
        FLevelUtils::FindStreamingLevel(World, FirstLevel->GetWorldAssetPackageFName()) == FirstLevel
        && FLevelUtils::FindStreamingLevel(World, SecondLevel->GetWorldAssetPackageFName()) == SecondLevel);
    TestTrue(TEXT("Both dynamic declarations permit engine streaming status replication"),
        FirstLevel->CanReplicateStreamingStatus() && SecondLevel->CanReplicateStreamingStatus());
    TestTrue(TEXT("Synthetic controllers complete the runtime initialization used by RPCs"),
        FirstPlayer->IsActorInitialized() && SecondPlayer->IsActorInitialized());
    TestEqual(TEXT("Fixture runs without a network driver"), World->GetNetMode(), NM_Standalone);
    TestNull(TEXT("First synthetic controller has no remote connection"), FirstPlayer->GetNetConnection());
    TestNull(TEXT("Second synthetic controller has no remote connection"), SecondPlayer->GetNetConnection());
    TestFalse(TEXT("Connectionless first controller is not a local player"), FirstPlayer->IsLocalController());
    TestFalse(TEXT("Connectionless second controller is not a local player"), SecondPlayer->IsLocalController());
    TSet<APlayerController*> Controllers;
    for (auto It = World->GetPlayerControllerIterator(); It; ++It) Controllers.Add(It->Get());
    TestTrue(TEXT("First synthetic controller participates in the server residency union"), Controllers.Contains(FirstPlayer));
    TestTrue(TEXT("Second synthetic controller participates in the server residency union"), Controllers.Contains(SecondPlayer));

    // A connectionless client RPC runs locally and can overwrite another player's server residency.
    FirstLevel->SetShouldBeLoaded(true); FirstLevel->SetShouldBeVisible(true);
    SecondPlayer->LevelStreamingStatusChanged(FirstLevel, false, false, false, INDEX_NONE);
    TestFalse(TEXT("Engine client notification without a connection changes this server's load flag"), FirstLevel->ShouldBeLoaded());
    TestFalse(TEXT("Engine client notification without a connection changes this server's visibility flag"), FirstLevel->GetShouldBeVisibleFlag());
    FirstLevel->SetShouldBeLoaded(false); FirstLevel->SetShouldBeVisible(false);
    SecondLevel->SetShouldBeLoaded(false); SecondLevel->SetShouldBeVisible(false);
    Streaming->UpdateStreaming();
    TestTrue(TEXT("First occupied zone remains requested by the server union"), FirstLevel->ShouldBeLoaded() && FirstLevel->GetShouldBeVisibleFlag());
    TestTrue(TEXT("Second occupied zone remains requested by the server union"), SecondLevel->ShouldBeLoaded() && SecondLevel->GetShouldBeVisibleFlag());
    TestTrue(TEXT("Connectionless controllers do not acquire per-client streaming state"), Streaming->ClientPackages.IsEmpty());

    UWarZoneStreamingSubsystem::FPending Request;
    Request.Player = FirstPlayer; Request.Destination = FirstZone->ZoneId;
    const double Deadline = World->GetTimeSeconds() + 30.0;
    const double GraceDeadline = World->GetTimeSeconds() + 5.0;
    Request.Deadline = Deadline;
    Streaming->Pending.Add(Request); Streaming->KeepUntil.Add(FirstZone->ZoneId, GraceDeadline);
    TestFalse(TEXT("A declared requested level has no actual readiness before loading"), Streaming->IsZoneReady(FirstZone->ZoneId, FirstPlayer));
    const FString SnapshotText = Streaming->DescribeZoneStreaming(FirstZone->ZoneId);
    TSharedPtr<FJsonObject> Snapshot;
    if (TestTrue(TEXT("Streaming diagnostic is valid JSON"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(SnapshotText), Snapshot)) && Snapshot)
    {
        TestTrue(TEXT("Snapshot identifies itself as diagnostic evidence"), Snapshot->GetBoolField(TEXT("diagnosticOnly")));
        const auto& Requests = Snapshot->GetArrayField(TEXT("requests"));
        if (TestEqual(TEXT("Snapshot retains the pending requester"), Requests.Num(), 1))
        {
            const auto Owner = Requests[0]->AsObject();
            TestTrue(TEXT("Snapshot proves the requester belongs to this world"), Owner->GetBoolField(TEXT("ownerInWorld")));
            TestFalse(TEXT("Snapshot distinguishes a requester without a network connection"), Owner->GetBoolField(TEXT("networkConnection")));
        }
        const auto& Levels = Snapshot->GetArrayField(TEXT("levels"));
        if (TestEqual(TEXT("Snapshot describes the one authored streaming declaration"), Levels.Num(), 1))
        {
            const auto Level = Levels[0]->AsObject();
            TestTrue(TEXT("Snapshot resolves the declared streaming level"), Level->GetBoolField(TEXT("declared")));
            TestTrue(TEXT("Snapshot records desired loading"), Level->GetBoolField(TEXT("shouldLoad")));
            TestTrue(TEXT("Snapshot records desired visibility"), Level->GetBoolField(TEXT("shouldBeVisible")));
            TestFalse(TEXT("Snapshot does not report desired loading as actual loading"), Level->GetBoolField(TEXT("loaded")));
            TestFalse(TEXT("Snapshot does not report desired visibility as actual visibility"), Level->GetBoolField(TEXT("visible")));
        }
    }
    TestEqual(TEXT("Snapshot preserves the pending request count"), Streaming->Pending.Num(), 1);
    TestEqual(TEXT("Snapshot preserves the original request deadline"), Streaming->Pending[0].Deadline, Deadline);
    TestEqual(TEXT("Snapshot preserves the zone grace lease"), Streaming->KeepUntil.FindRef(FirstZone->ZoneId), GraceDeadline);
    TestTrue(TEXT("Snapshot preserves both server residency requests"), FirstLevel->ShouldBeLoaded() && FirstLevel->GetShouldBeVisibleFlag()
        && SecondLevel->ShouldBeLoaded() && SecondLevel->GetShouldBeVisibleFlag());
    TestFalse(TEXT("Snapshot cannot load or reveal the destination"), FirstLevel->IsLevelLoaded() || FirstLevel->IsLevelVisible());
    TestFalse(TEXT("Snapshot cannot grant destination readiness"), Streaming->IsZoneReady(FirstZone->ZoneId, FirstPlayer));
    Streaming->Pending.Reset(); Streaming->KeepUntil.Remove(FirstZone->ZoneId);
    World->DestroyWorld(false); GEngine->DestroyWorldContext(World);
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
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Editor, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Portal range fixture"), World)) return false;
    auto* Portal = World->SpawnActor<AWarZonePortal>();
    auto* Player = World->SpawnActor<AWarZonePortal>();
    auto* Sphere = Cast<USphereComponent>(Portal->GetRootComponent());
    TestNotNull(TEXT("Portal trigger"), Sphere);
    Player->SetActorLocation(FVector(930,0,0));
    TestFalse(TEXT("Initial capsule contact is outside center admission"), Portal->IsWithinEntryRange(Player));
    Player->SetActorLocation(FVector(899,0,0));
    TestTrue(TEXT("Continued walking enters without a second BeginOverlap"), Portal->IsWithinEntryRange(Player));
    TestTrue(TEXT("Portal continues checking admission after initial contact"), Portal->PrimaryActorTick.bCanEverTick);
    TestFalse(TEXT("A missing pawn is never eligible"), Portal->IsWithinEntryRange(nullptr));
    Portal->SetActorScale3D(FVector(2));
    Player->SetActorLocation(FVector(1799,0,0));
    TestTrue(TEXT("Interaction uses actual scaled trigger range"), Portal->IsWithinEntryRange(Player));
    auto* Capital = World->SpawnActor<AWarZoneAnchor>(); Capital->ZoneId = TEXT("aegis_capital"); Capital->HalfSize = 5000;
    auto* Campaign = World->SpawnActor<AWarSiegeEncounter>(); Campaign->bCampaign = true; Campaign->ActivationId = TEXT("portal-scope"); Campaign->Siege.Phase = EWarSiegePhase::Active;
    auto* Scenario = World->SpawnActor<AWarSiegeEncounter>();
    auto* Character = World->SpawnActor<AWarCharacter>(); auto* State = World->SpawnActor<AWarPlayerState>();
    Character->SetPlayerState(State); State->SetDevelopmentRealm(EWarRealm::Aegis); State->SetSiegeMembership(Campaign);
    Character->SetActorLocation(FVector(200000,0,0)); State->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
    const auto BlocksDeparture = &AWarZonePortal::BlocksSiegeDeparture;
    TestFalse(TEXT("Remote reserved seat can follow intermediate approach portals"), BlocksDeparture(Character, TEXT("sunmeadow_march")));
    TestFalse(TEXT("Remote reserved seat can enter the capital through its validated portal"), BlocksDeparture(Character, TEXT("aegis_capital")));
    TestFalse(TEXT("Remote character never receives capital siege protection"), Campaign->IsProtected(Character));
    TestFalse(TEXT("Remote death retains ordinary campaign respawn handling"), Campaign->HandlesDeath(Character));
    State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
    TestFalse(TEXT("A zone label alone cannot physically admit a remote seat"), BlocksDeparture(Character, TEXT("dawnline_expanse")));
    Character->SetActorLocation(FVector(1000,0,0));
    TestTrue(TEXT("Physically admitted capital participant must leave before departing"), BlocksDeparture(Character, TEXT("dawnline_expanse")));
    TestFalse(TEXT("A capital destination remains available to its approved participant"), BlocksDeparture(Character, TEXT("aegis_capital")));
    State->SetSiegeMembership(Scenario); Character->SetActorLocation(FVector(200000,0,0)); State->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
    TestTrue(TEXT("Scenario membership still forbids leaving the isolated siege"), BlocksDeparture(Character, TEXT("sunmeadow_march")));
    State->SetSiegeMembership(nullptr);
    TestFalse(TEXT("Unrelated world players retain ordinary travel"), BlocksDeparture(Character, TEXT("sunmeadow_march")));
    TestFalse(TEXT("Missing character has no siege membership"), BlocksDeparture(nullptr, TEXT("sunmeadow_march")));
    World->DestroyWorld(false);
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
