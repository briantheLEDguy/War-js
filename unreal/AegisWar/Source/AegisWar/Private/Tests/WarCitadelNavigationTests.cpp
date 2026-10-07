#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeNavigation.h"
#include "WarCitadelNavigationFilter.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeBattlefield.h"
#include "WarPlayerState.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Misc/ScopeExit.h"
#include "Components/BoxComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelNavigationScopeTest,"AegisWar.Foundation.CitadelNavigationScope",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelNavigationScopeTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();
    auto* Field=World->SpawnActor<AWarSiegeBattlefield>();Encounter->Battlefield=Field;
    auto* Member=World->SpawnActor<AWarPlayerState>();
    auto* Visitor=World->SpawnActor<AWarPlayerState>();
    Field->DefinitionVersion=2;Encounter->Siege.RulesVersion=2;
    TestEqual(TEXT("Readiness uses the bounded citadel query before enrollment"),
        Field->NavigationFilter().Get(),UWarCitadelNavigationFilter::StaticClass());
    TestNull(TEXT("Missing actor retains engine defaults"),WarSiegeNavigation::FilterFor(nullptr).Get());
    TestNull(TEXT("An ordinary capital visitor retains engine defaults"),WarSiegeNavigation::FilterFor(Visitor).Get());
    Member->SetSiegeMembership(Encounter);
    TestEqual(TEXT("Owned v2 member uses the expanded citadel filter"),
        WarSiegeNavigation::FilterFor(Member).Get(),UWarCitadelNavigationFilter::StaticClass());
    TestEqual(TEXT("Readiness and actual members share one query policy"),
        WarSiegeNavigation::FilterFor(Member).Get(),Field->NavigationFilter().Get());
    Encounter->Siege.RulesVersion=1;
    TestNull(TEXT("Recorded v1 rounds retain their original query policy"),WarSiegeNavigation::FilterFor(Member).Get());
    Encounter->Siege.RulesVersion=2;Field->DefinitionVersion=1;
    TestNull(TEXT("Legacy readiness retains engine query policy"),Field->NavigationFilter().Get());
    TestNull(TEXT("Legacy physical layouts retain engine defaults"),WarSiegeNavigation::FilterFor(Member).Get());
    Field->DefinitionVersion=2;Encounter->Battlefield=nullptr;
    TestNull(TEXT("Missing physical definition cannot enable the larger query"),WarSiegeNavigation::FilterFor(Member).Get());
    Encounter->Battlefield=Field;Member->SetSiegeMembership(nullptr);
    TestNull(TEXT("Returned characters lose encounter query policy"),WarSiegeNavigation::FilterFor(Member).Get());
    TestNull(TEXT("Another player remains unaffected through the transitions"),WarSiegeNavigation::FilterFor(Visitor).Get());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelProjectedFloorTest,"AegisWar.Foundation.CitadelProjectedFloor",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelProjectedFloorTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Surface=World->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Surface);Surface->SetRootComponent(Box);
    Box->SetBoxExtent(FVector(500,500,10));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Box->SetCollisionObjectType(ECC_WorldStatic);Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->RegisterComponent();Surface->SetActorLocation(FVector(0,0,-10));
    FHitResult Hit;
    TestTrue(TEXT("A collision floor below a raised rasterized ramp point is usable"),
        WarSiegeNavigation::ProjectedFloor(World,FVector(0,0,98.6),Hit));
    TestTrue(TEXT("The actual collision elevation is returned, not the nav polygon elevation"),FMath::Abs(Hit.ImpactPoint.Z)<.01);
    TestTrue(TEXT("The bounded lower edge remains usable"),WarSiegeNavigation::ProjectedFloor(World,FVector(0,0,199),Hit));
    TestFalse(TEXT("A lower storey cannot be selected beyond the bounded band"),WarSiegeNavigation::ProjectedFloor(World,FVector(0,0,201),Hit));
    TestFalse(TEXT("An upper storey cannot be selected above the bounded band"),WarSiegeNavigation::ProjectedFloor(World,FVector(0,0,-26),Hit));
    TestFalse(TEXT("Ignoring a surface does not invent a floor"),WarSiegeNavigation::ProjectedFloor(World,FVector::ZeroVector,Hit,Surface));
    Box->SetCollisionObjectType(ECC_Pawn);
    TestFalse(TEXT("A standing pawn cannot become a walkable static floor"),WarSiegeNavigation::ProjectedFloor(World,FVector::ZeroVector,Hit));
    Box->SetCollisionObjectType(ECC_WorldStatic);Surface->SetActorRotation(FRotator(70,0,0));
    TestFalse(TEXT("A steep collision face remains unwalkable"),WarSiegeNavigation::ProjectedFloor(World,FVector(0,0,100),Hit));
    TestFalse(TEXT("A missing world fails closed"),WarSiegeNavigation::ProjectedFloor(nullptr,FVector::ZeroVector,Hit));
    return !HasAnyErrors();
}
#endif
