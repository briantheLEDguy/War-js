#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCitadelSiegeProof.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeBattlefield.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelTacticalTargetsTest,"AegisWar.Foundation.CitadelTacticalTargets",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelTacticalTargetsTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();auto* Foreign=World->SpawnActor<AWarSiegeEncounter>();
    Encounter->Battlefield=World->SpawnActor<AWarSiegeBattlefield>();Encounter->Siege.Phase=EWarSiegePhase::Active;
    Encounter->Battlefield->TeamSpawns={{10000,0,0},{-10000,0,0}};
    const auto Spawn=[&](EWarRealm Realm,const FVector& Position,EWarSiegeUnit Unit) {
        auto* Controller=World->SpawnActor<AWarPlayerController>();auto* State=World->SpawnActor<AWarPlayerState>();
        FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=World->SpawnActor<AWarCharacter>(Position,FRotator::ZeroRotator,Params);
        Controller->PlayerState=State;State->SetOwner(Controller);Controller->Possess(Pawn);Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(Realm);State->SetCurrentZoneTrusted(TEXT("aegis_capital"));State->SetSiegeMembership(Encounter,Unit);
        // Eligibility-only fixture; it does not render, equip models or certify visual readiness.
        Pawn->bVisualReady=true;return Pawn;
    };
    auto* Source=Spawn(EWarRealm::Riftbound,{0,0,100},EWarSiegeUnit::Participant);
    auto* Enemy=Spawn(EWarRealm::Aegis,{1000,0,100},EWarSiegeUnit::Participant);
    const auto CanTarget=[&](AWarCharacter* Target){return WarCitadelProofTactics::CanTarget(Encounter,Source,Target,2500);};
    TestTrue(TEXT("An opposing enrolled participant is a legal fixture target"),CanTarget(Enemy));
    Enemy->GetPlayerState<AWarPlayerState>()->SetSiegeMembership(Encounter,EWarSiegeUnit::Guard);
    TestTrue(TEXT("An opposing owned guard remains a legal target"),CanTarget(Enemy));
    Enemy->GetPlayerState<AWarPlayerState>()->SetSiegeMembership(Foreign,EWarSiegeUnit::Participant);
    TestFalse(TEXT("Foreign encounter targets remain excluded"),CanTarget(Enemy));
    Enemy->GetPlayerState<AWarPlayerState>()->SetSiegeMembership(Encounter,EWarSiegeUnit::Participant);
    TestFalse(TEXT("Self remains excluded"),CanTarget(Source));
    auto* Ally=Spawn(EWarRealm::Riftbound,{0,1000,100},EWarSiegeUnit::Participant);
    TestFalse(TEXT("An owned ally remains excluded"),CanTarget(Ally));
    Enemy->bDead=true;TestFalse(TEXT("Dead targets remain excluded"),CanTarget(Enemy));Enemy->bDead=false;
    Enemy->SetActorHiddenInGame(true);TestFalse(TEXT("Hidden targets remain excluded"),CanTarget(Enemy));Enemy->SetActorHiddenInGame(false);
    Enemy->SetActorLocation({3000,0,100});TestFalse(TEXT("Ordinary range remains enforced"),CanTarget(Enemy));Enemy->SetActorLocation({1000,0,100});
    Encounter->Battlefield->TeamSpawns[0]=Enemy->GetActorLocation();
    TestTrue(TEXT("The target is actually spawn protected"),Encounter->IsProtected(Enemy));
    TestFalse(TEXT("Spawn protection is never bypassed by fixture targeting"),CanTarget(Enemy));
    Encounter->Battlefield->TeamSpawns[0]={10000,0,0};
    auto* Obstacle=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Obstacle);Obstacle->SetRootComponent(Box);
    Box->SetBoxExtent({20,200,200});Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Box->SetCollisionObjectType(ECC_WorldStatic);Box->SetCollisionResponseToAllChannels(ECR_Ignore);
    Box->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);Box->RegisterComponent();Obstacle->SetActorLocation({500,0,100});
    TestFalse(TEXT("Actual blocking geometry retains line-of-sight restrictions"),CanTarget(Enemy));
    Obstacle->Destroy();TestTrue(TEXT("Removing the obstruction restores the ordinary target"),CanTarget(Enemy));
    return !HasAnyErrors();
}
#endif
