#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarPortalLanding.h"
#include "WarCharacter.h"
#include "WarZoneAnchor.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarPortalLandingTest,"AegisWar.Foundation.PortalEvacuationLanding",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarPortalLandingTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!TestNotNull(TEXT("Portal collision world"),World)) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());World->BeginPlay();World->GetWorldSettings()->NotifyBeginPlay();
    const auto Box=[&](FVector Position,FVector Extent) {
        auto* Actor=World->SpawnActor<AActor>();auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->SetRootComponent(Shape);Shape->SetBoxExtent(Extent);Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Shape->SetCollisionObjectType(ECC_WorldStatic);Shape->SetCollisionResponseToAllChannels(ECR_Block);
        Shape->RegisterComponent();Actor->SetActorLocation(Position);return Actor;
    };
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const auto Character=[&](FVector Position) { return World->SpawnActor<AWarCharacter>(Position,FRotator::ZeroRotator,Spawn); };
    auto* Zone=World->SpawnActor<AWarZoneAnchor>();Zone->ZoneId=TEXT("sunmeadow_march");Zone->HalfSize=5000;
    auto* Floor=Box(FVector(0,0,-10),FVector(3000,3000,10));
    auto* Probe=Character(FVector(-2000,0,101));
    auto* Occupant=Character(FVector(0,0,101));
    FVector Landing(777);FString Error;
    TestFalse(TEXT("Normal travel cannot stack a new arrival on a standing character"),
        WarPortalLanding::Find(Probe,FVector::ZeroVector,Zone,0,nullptr,nullptr,Landing,Error));
    TestEqual(TEXT("Blocked landing leaves the caller's transform unchanged"),Landing,FVector(777));
    TArray<AWarCharacter*> Crowd{Occupant};
    for (int32 Index=1;Index<18;++Index)
    {
        if (!TestTrue(TEXT("Eighteen stationary evacuees fit on connected checked ground"),
            WarPortalLanding::Find(Probe,FVector::ZeroVector,Zone,600,nullptr,nullptr,Landing,Error))) break;
        TestTrue(TEXT("Arrival remains on the actual floor, never another capsule"),FMath::Abs(Landing.Z-101)<.01);
        TestTrue(TEXT("Arrival stays inside the bounded pad"),Landing.Size2D()<=600.01);
        for (const auto* Other:Crowd) TestTrue(TEXT("Landing reserves full character clearance"),
            FVector::Dist2D(Landing,Other->GetActorLocation())>=84);
        Crowd.Add(Character(Landing));
    }
    TestEqual(TEXT("Every crowd member has a distinct safe physical arrival"),Crowd.Num(),18);
    for (auto* Pawn:Crowd) Pawn->Destroy();
    TestTrue(TEXT("Unoccupied normal travel keeps the exact authored horizontal arrival"),
        WarPortalLanding::Find(Probe,FVector::ZeroVector,Zone,0,nullptr,nullptr,Landing,Error));
    TestEqual(TEXT("Normal arrival X"),Landing.X,0.);TestEqual(TEXT("Normal arrival Y"),Landing.Y,0.);
    Floor->Destroy();
    Box(FVector(0,0,-10),FVector(55,55,10));
    Box(FVector(300,0,-10),FVector(55,55,10));
    auto* Blocking=Character(FVector(0,0,101));
    Landing=FVector(777);
    TestFalse(TEXT("A clear disconnected island cannot become evacuation space"),
        WarPortalLanding::Find(Probe,FVector::ZeroVector,Zone,600,nullptr,nullptr,Landing,Error));
    TestEqual(TEXT("Missing connected space retains the original transform"),Landing,FVector(777));
    Blocking->Destroy();
    TestFalse(TEXT("An absent floor is recoverable"),
        WarPortalLanding::Find(Probe,FVector(1200,1200,0),Zone,600,nullptr,nullptr,Landing,Error));
    TestFalse(TEXT("Search cannot escape the bounded arrival radius"),
        WarPortalLanding::Find(Probe,FVector::ZeroVector,Zone,601,nullptr,nullptr,Landing,Error));
    Zone->HalfSize=100;
    auto* Ambiguous=World->SpawnActor<AWarZoneAnchor>();Ambiguous->HalfSize=100;
    TestFalse(TEXT("Ambiguous destination ownership cannot admit travel"),
        WarPortalLanding::Find(Probe,FVector::ZeroVector,Zone,600,nullptr,nullptr,Landing,Error));
    World->EndPlay(EEndPlayReason::Quit);GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
    return !HasAnyErrors();
}
#endif
