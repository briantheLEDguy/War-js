#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeEscort.h"
#include "WarSiegeEncounter.h"
#include "WarPlayerState.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeEscortTest,"AegisWar.Foundation.SiegeEscortClearance",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSiegeEscortTest::RunTest(const FString& Parameters)
{
    for (float Yaw:{0.f,45.f,90.f,-175.f})
    {
        const FQuat Heading=FRotator(0,Yaw,0).Quaternion();
        const TArray<FWarSiegeEscortHull> Hulls={
            {FVector(0,0,155),Heading,FVector(240,175,120)},
            {Heading.RotateVector(FVector(-850,0,155)),Heading,FVector(240,175,120)}};
        for (int32 Seat=0;Seat<18;++Seat)
        {
            const FVector Offset=WarSiegeEscort::Offset(Seat,Yaw);
            TestTrue(TEXT("Every flank seat fits the actual 650 cm capture radius and approach clamp"),Offset.Size2D()<=490);
            TestTrue(TEXT("All eighteen seats clear both rotated hulls and steering margins"),
                WarSiegeEscort::PointClear(Offset+FVector(0,0,99),Hulls,42,96));
            for (int32 Other=0;Other<Seat;++Other)
                TestTrue(TEXT("Flank seats reserve separate full 84 cm capsules"),FVector::Dist2D(Offset,WarSiegeEscort::Offset(Other,Yaw))>84);
        }
        const auto Rotate=[&](FVector P) { return Heading.RotateVector(P); };
        const TArray<FVector> Through={Rotate(FVector(-1600,0,0)),Rotate(FVector(1000,0,0))};
        TestFalse(TEXT("Clear endpoints cannot excuse a path through either cart"),WarSiegeEscort::PathClear(Through,Hulls,42,96));
        const TArray<FVector> Flank={Rotate(FVector(-1600,0,0)),Rotate(FVector(-1600,800,0)),Rotate(FVector(1000,800,0))};
        TestTrue(TEXT("An ordinary flank path clears both cart footprints"),WarSiegeEscort::PathClear(Flank,Hulls,42,96));
        const TArray<FVector> Escape={FVector::ZeroVector,Rotate(FVector(0,800,0))};
        TestTrue(TEXT("An obstructed capsule can leave the reservation"),WarSiegeEscort::PathClear(Escape,Hulls,42,96));
        const TArray<FVector> Reenter={FVector::ZeroVector,Rotate(FVector(0,800,0)),FVector::ZeroVector};
        TestFalse(TEXT("Escape cannot justify later re-entry"),WarSiegeEscort::PathClear(Reenter,Hulls,42,96));
    }
    const TArray<FWarSiegeEscortHull> Hulls={{FVector(0,0,155),FQuat::Identity,FVector(240,175,120)}};
    TestFalse(TEXT("A capsule on the expanded face still needs clearance"),WarSiegeEscort::PointClear(FVector(0,317,99),Hulls,42,96));
    TestTrue(TEXT("A capsule outside the expanded face is clear"),WarSiegeEscort::PointClear(FVector(0,318,99),Hulls,42,96));
    TestFalse(TEXT("An unfinished escape cannot be used as an approach path"),WarSiegeEscort::PathClear(TArray<FVector>{FVector::ZeroVector,FVector(0,100,0)},Hulls,42,96));
    TestFalse(TEXT("Invalid capsule dimensions fail closed"),WarSiegeEscort::PointClear(FVector(0,800,99),Hulls,42,20));
    TestFalse(TEXT("A short corner crossing cannot hide between sample endpoints"),
        WarSiegeEscort::PathClear(TArray<FVector>{FVector(389,309,0),FVector(374,324,0)},Hulls,42,96));
    TestTrue(TEXT("The complete live corner path clears the reservation"),
        WarSiegeEscort::PathClear(TArray<FVector>{FVector(390,280,0),FVector(390,330,0),FVector(310,330,0)},Hulls,42,96));
    TestFalse(TEXT("Skipping a nearby live corner must revalidate the actual movement chord"),
        WarSiegeEscort::PathClear(TArray<FVector>{FVector(390,280,0),FVector(310,330,0)},Hulls,42,96));
    TestFalse(TEXT("An obstructed edge pawn cannot first move deeper into the hull"),
        WarSiegeEscort::PathClear(TArray<FVector>{FVector(0,300,0),FVector(0,0,0),FVector(0,800,0)},Hulls,42,96));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeEscortSeatTest,"AegisWar.Foundation.SiegeEscortSeats",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSiegeEscortSeatTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();
    const auto Add=[&]() {
        auto* Bot=World->SpawnActor<AWarSiegeBotController>();auto* State=World->SpawnActor<AWarPlayerState>();
        Bot->PlayerState=State;State->SetOwner(Bot);State->SetDevelopmentRealm(EWarRealm::Riftbound);
        State->SetSiegeMembership(Encounter);Encounter->Units.Add(Bot);return Bot;
    };
    auto* First=Add();auto* Survivor=Add();Encounter->AssignSquads();
    TestEqual(TEXT("First available escort seats are distinct"),First->EscortSeat,0);
    TestEqual(TEXT("Second bot receives the next seat"),Survivor->EscortSeat,1);
    First->Destroy();auto* Replacement=Add();Encounter->AssignSquads();
    TestEqual(TEXT("A survivor does not reshuffle when another controller is lost"),Survivor->EscortSeat,1);
    TestEqual(TEXT("A replacement reclaims the vacant seat"),Replacement->EscortSeat,0);
    return !HasAnyErrors();
}
#endif
