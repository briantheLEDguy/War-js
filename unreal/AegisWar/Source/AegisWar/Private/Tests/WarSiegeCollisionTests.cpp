#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeEquipment.h"
#include "WarCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeCollisionTest,"AegisWar.Foundation.SiegeEquipmentCollision",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSiegeCollisionTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());World->BeginPlay();World->GetWorldSettings()->NotifyBeginPlay();
    const auto Box=[&](FVector Position,FVector Extent,ECollisionChannel Channel) {
        auto* Actor=World->SpawnActor<AActor>();auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->SetRootComponent(Shape);Shape->SetBoxExtent(Extent);Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Shape->SetCollisionObjectType(Channel);Shape->SetCollisionResponseToAllChannels(ECR_Block);
        Shape->RegisterComponent();Actor->SetActorLocation(Position);return Actor;
    };
    Box(FVector(0,0,-10),FVector(3000,3000,10),ECC_WorldStatic);
    auto* Vehicle=World->SpawnActor<AWarSiegeEquipment>();
    Vehicle->Definition=NewObject<UWarSiegeEquipmentDefinition>(Vehicle);
    auto* Occupant=Box(FVector(0,0,96),FVector(42,42,96),ECC_Pawn);
    TestFalse(TEXT("Full-size hull cannot spawn over a participant"),Vehicle->TryPlace());
    TestFalse(TEXT("Blocked placement never enables the engine"),Vehicle->IsPlaced());
    TestEqual(TEXT("Spawn does not move the occupant"),Occupant->GetActorLocation(),FVector(0,0,96));
    Occupant->SetActorLocation(FVector(1000,1000,96));
    TestTrue(TEXT("Placement retries when the staging area clears"),Vehicle->TryPlace());
    Occupant->SetActorLocation(FVector(450,0,96));
    TestFalse(TEXT("Advancing hull stops before a participant"),Vehicle->MovementClear(FVector(500,0,0),FRotator::ZeroRotator));
    Occupant->SetActorLocation(FVector(1000,1000,96));
    TestTrue(TEXT("An empty road allows movement"),Vehicle->MovementClear(FVector(500,0,0),FRotator::ZeroRotator));
    // This point is outside both endpoint boxes but inside the corner's arc.
    auto* Corner=Box(FVector(200,200,155),FVector(3),ECC_WorldDynamic);
    TestTrue(TEXT("Rotation start is clear"),Vehicle->PoseClear(FVector::ZeroVector,FQuat::Identity));
    TestTrue(TEXT("Rotation end is clear"),Vehicle->PoseClear(FVector::ZeroVector,FRotator(0,90,0).Quaternion()));
    TestFalse(TEXT("Rotation cannot sweep through an intervening obstacle"),Vehicle->MovementClear(FVector::ZeroVector,FRotator(0,90,0)));
    Corner->Destroy();
    const FVector Elevated(0,0,200);
    TestTrue(TEXT("The tilted hull is clear before adding the wall"),Vehicle->PoseClear(Elevated,FRotator(35,0,0).Quaternion()));
    auto* SlopeObstacle=Box(FVector(-300,0,300),FVector(3),ECC_WorldStatic);
    TestTrue(TEXT("The flat hull clears the slope-side obstacle"),Vehicle->PoseClear(Elevated,FQuat::Identity));
    TestFalse(TEXT("Terrain tilt cannot bypass a collision outside the flat navigation footprint"),
        Vehicle->PoseClear(Elevated,FRotator(35,0,0).Quaternion()));
    SlopeObstacle->Destroy();
    FActorSpawnParameters Correction;Correction.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* CorrectionPawn=World->SpawnActor<AWarCharacter>(FVector(0,0,96),FRotator::ZeroRotator,Correction);
    Vehicle->Tick(.016f);
    TestTrue(TEXT("A penetrating capsule can escape when no navigation recovery point exists"),
        CorrectionPawn->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Vehicle));
    CorrectionPawn->SetActorLocation(FVector(800,0,96));Vehicle->Tick(.016f);
    TestFalse(TEXT("Normal engine collision resumes once the capsule is outside"),
        CorrectionPawn->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Vehicle));
    World->EndPlay(EEndPlayReason::Quit);GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
    return !HasAnyErrors();
}
#endif
