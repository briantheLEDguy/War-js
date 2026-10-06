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
    TestNull(TEXT("Missing actor retains engine defaults"),WarSiegeNavigation::FilterFor(nullptr).Get());
    TestNull(TEXT("An ordinary capital visitor retains engine defaults"),WarSiegeNavigation::FilterFor(Visitor).Get());
    Member->SetSiegeMembership(Encounter);
    TestEqual(TEXT("Owned v2 member uses the expanded citadel filter"),
        WarSiegeNavigation::FilterFor(Member).Get(),UWarCitadelNavigationFilter::StaticClass());
    Encounter->Siege.RulesVersion=1;
    TestNull(TEXT("Recorded v1 rounds retain their original query policy"),WarSiegeNavigation::FilterFor(Member).Get());
    Encounter->Siege.RulesVersion=2;Field->DefinitionVersion=1;
    TestNull(TEXT("Legacy physical layouts retain engine defaults"),WarSiegeNavigation::FilterFor(Member).Get());
    Field->DefinitionVersion=2;Encounter->Battlefield=nullptr;
    TestNull(TEXT("Missing physical definition cannot enable the larger query"),WarSiegeNavigation::FilterFor(Member).Get());
    Encounter->Battlefield=Field;Member->SetSiegeMembership(nullptr);
    TestNull(TEXT("Returned characters lose encounter query policy"),WarSiegeNavigation::FilterFor(Member).Get());
    TestNull(TEXT("Another player remains unaffected through the transitions"),WarSiegeNavigation::FilterFor(Visitor).Get());
    return !HasAnyErrors();
}
#endif
