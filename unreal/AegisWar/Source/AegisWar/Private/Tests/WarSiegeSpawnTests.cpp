#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeNavigation.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeSpawnTest,"AegisWar.Foundation.SiegeSpawnClearance",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarSiegeSpawnTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL()); World->BeginPlay(); World->GetWorldSettings()->NotifyBeginPlay();
    const auto Box=[&](FVector Position,FVector Extent,ECollisionChannel ObjectType) {
        auto* Actor=World->SpawnActor<AActor>(); auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->SetRootComponent(Shape); Shape->SetBoxExtent(Extent);
        Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Shape->SetCollisionObjectType(ObjectType);
        Shape->SetCollisionResponseToAllChannels(ECR_Block); Shape->RegisterComponent(); Actor->SetActorLocation(Position);
        return Actor;
    };
    Box(FVector(0,0,-10),FVector(1000,1000,10),ECC_WorldStatic);
    FVector Center;
    TestTrue(TEXT("Empty grounded spawn fits the full capsule"),WarSiegeNavigation::SpawnCandidate(World,FVector::ZeroVector,42,96,Center));
    TestTrue(TEXT("Spawn feet clear the floor"),Center.Z>=99 && Center.Z<101);
    auto* Occupant=Box(FVector(0,0,96),FVector(42,42,96),ECC_Pawn);
    TestFalse(TEXT("A standing participant blocks respawn"),WarSiegeNavigation::SpawnCandidate(World,FVector::ZeroVector,42,96,Center));
    TestTrue(TEXT("A nearby empty point is usable without moving the occupant"),WarSiegeNavigation::SpawnCandidate(World,FVector(150,0,0),42,96,Center));
    TestEqual(TEXT("Occupied participant is not teleported"),Occupant->GetActorLocation(),FVector(0,0,96));
    Box(FVector(150,0,150),FVector(20,100,150),ECC_WorldStatic);
    TestFalse(TEXT("Static obstructions also block the candidate"),WarSiegeNavigation::SpawnCandidate(World,FVector(150,0,0),42,96,Center));
    TestFalse(TEXT("Missing floor cannot spawn a falling combatant"),WarSiegeNavigation::SpawnCandidate(World,FVector(2000,0,0),42,96,Center));
    World->EndPlay(EEndPlayReason::Quit); GEngine->DestroyWorldContext(World); World->DestroyWorld(false);
    return !HasAnyErrors();
}
#endif
