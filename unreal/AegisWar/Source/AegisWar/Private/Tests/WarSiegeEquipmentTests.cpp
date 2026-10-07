#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeRules.h"
#include "WarSiegeEquipment.h"
#include "WarCharacter.h"
#include "WarSiegeEncounter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "Misc/ScopeExit.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeOwnershipTest,"AegisWar.Foundation.SiegeOwnership",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSiegeOwnershipTest::RunTest(const FString& Parameters)
{
    FWarSiegeState S; WarSiege::Start(S,6,EWarSiegeScenario::LowerCity);
    FWarSiegePresence P; P.Attackers=6;
    WarSiege::Tick(S,P,20);
    TestEqual(TEXT("Partial capture does not raise a standard"),WarSiege::ClaimedObjectives(S),uint16(0));
    P.Defenders=1; WarSiege::Tick(S,P,20);
    TestEqual(TEXT("Contesting cannot claim ownership"),WarSiege::ClaimedObjectives(S),uint16(0));
    P.Defenders=0; WarSiege::Tick(S,P,30);
    TestEqual(TEXT("Supply claim raises only its standard"),WarSiege::ClaimedObjectives(S),uint16(1));
    P.bEscortAtCheckpoint=false;WarSiege::Tick(S,P,100);
    TestEqual(TEXT("Timer cannot raise a checkpoint standard ahead of the convoy"),WarSiege::ClaimedObjectives(S),uint16(1));
    P.bEscortAtCheckpoint=true;
    for (int I=0;I<3;++I) WarSiege::Tick(S,P,100);
    TestEqual(TEXT("Lower-city win owns exactly four objectives"),WarSiege::ClaimedObjectives(S),uint16(15));
    S.bAttackersWon=false;
    TestEqual(TEXT("Defender result preserves claims"),WarSiege::ClaimedObjectives(S),uint16(15));
    WarSiege::Start(S,6,EWarSiegeScenario::LowerCity);
    TestEqual(TEXT("Rematch clears ownership"),WarSiege::ClaimedObjectives(S),uint16(0));
    S.Phase=EWarSiegePhase::Waiting;S.MilestoneSeconds.Add(1);
    TestEqual(TEXT("Lobby never displays stale ownership"),WarSiege::ClaimedObjectives(S),uint16(0));
    S.Phase=EWarSiegePhase::Active;S.OptionalClaims=5;S.RulesVersion=1;
    TestEqual(TEXT("Optional claims survive stage transitions"),WarSiege::ClaimedObjectives(S),uint16(1281));
    S={};WarSiege::Start(S,6);P={};P.OptionalAttackers=6;
    WarSiege::Tick(S,P,45);
    TestEqual(TEXT("Completing sabotage claims its standard"),WarSiege::ClaimedObjectives(S),uint16(256));
    S.Stage=1;S.bOptionalComplete=false;S.OptionalProgress=0;
    WarSiege::Tick(S,P,45);
    TestEqual(TEXT("A later optional claim preserves the earlier standard"),WarSiege::ClaimedObjectives(S),uint16(768));
    UWarSiegeEquipmentDefinition* Definition=NewObject<UWarSiegeEquipmentDefinition>();FString Error;
    TestFalse(TEXT("Missing or unreviewed engine cannot spawn a fallback"),Definition->Validate(Error));
    const TArray<FVector> Trail{FVector::ZeroVector,FVector(1000,0,0),FVector(1000,1000,500)};
    TestTrue(TEXT("Following an incline interpolates the travelled ground height"),
        WarSiegeEquipment::TrailingPoint(Trail,850).Equals(FVector(1000,150,75),.001));
    TestTrue(TEXT("The support engine follows the corner instead of cutting through it"),
        WarSiegeEquipment::TrailingPoint(Trail,1300).Equals(FVector(700,0,0),.001));
    TestTrue(TEXT("The initial convoy spacing extends behind its spawn heading"),
        WarSiegeEquipment::TrailingPoint(Trail,2300).Equals(FVector(-300,0,0),.001));
    for (const FVector& Grades:{FVector(0,0,0),FVector(.6,.2,0),FVector(-.4,-.3,0)})
    {
        const FRotator Pose=WarSiegeEquipment::SurfaceRotation(37,Grades.X,Grades.Y);
        TestEqual(TEXT("Cross slope never changes the steering heading"),Pose.Yaw,37.);
        for (const FVector& Corner:{FVector(245,178,0),FVector(245,-178,0),FVector(-245,178,0),FVector(-245,-178,0)})
        {
            const FVector Aligned=FRotator(0,-37,0).RotateVector(Pose.RotateVector(Corner));
            TestTrue(TEXT("All four support points lie on the ground plane"),
                FMath::IsNearlyEqual(Aligned.Z,Grades.X*Aligned.X+Grades.Y*Aligned.Y,.001));
        }
    }
    for (const FVector& Extent : {FVector(245,178,120), FVector(210,178,120)})
        for (float Yaw : {0.f,37.f,90.f})
            for (float X : {-1.f,1.f}) for (float Y : {-1.f,1.f}) for (float Z : {-1.f,1.f})
            {
                const FVector Corner=FRotator(0,Yaw,0).RotateVector(Extent*FVector(X,Y,Z)+FVector(0,0,155));
                TestTrue(TEXT("Convoy navigation encloses the flat hull diagonal with sweep clearance"),
                    Corner.Size2D()+8 <= WarSiegeEquipment::NavigationRadius);
                TestTrue(TEXT("Convoy height covers the offset flat hull"), Corner.Z+8 <= WarSiegeEquipment::NavigationHeight);
            }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeMovementEnvelopeTest,"AegisWar.Foundation.SiegeMovementEnvelope",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSiegeMovementEnvelopeTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Vehicle=World->SpawnActor<AWarSiegeEquipment>();
    Vehicle->Definition=NewObject<UWarSiegeEquipmentDefinition>();
    Vehicle->Definition->HullExtent=FVector(245,178,120);
    auto* Pawn=World->SpawnActor<AWarCharacter>();
    auto* Capsule=Pawn->GetCapsuleComponent();
    Capsule->SetCapsuleSize(42,96);Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Capsule->SetCollisionObjectType(ECC_Pawn);Capsule->SetCollisionResponseToAllChannels(ECR_Block);
    Pawn->SetActorLocation(FVector(196,222,98.15));
    const FVector HullCenter(0,0,155);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeEnvelopeTest),false,Vehicle);
    TArray<FOverlapResult> Bare,Recovery;
    TestFalse(TEXT("A nearby capsule may clear the unpadded hull"),
        World->OverlapMultiByObjectType(Bare,HullCenter,FQuat::Identity,FCollisionObjectQueryParams(ECC_Pawn),
            FCollisionShape::MakeBox(Vehicle->Definition->HullExtent),Query));
    TestFalse(TEXT("The same capsule still blocks the real padded movement sweep"),
        Vehicle->MovementClear(FVector::ZeroVector,FRotator::ZeroRotator));
    TestTrue(TEXT("The recovery query covers this actual sweep blocker"),
        WarSiegeEquipment::MovementContacts(World,HullCenter,FQuat::Identity,Vehicle->Definition->HullExtent,Query,Recovery));
    TestTrue(TEXT("The exact blocked character is available for ordinary recovery"),
        Recovery.ContainsByPredicate([&](const FOverlapResult& Hit) { return Hit.GetActor()==Pawn; }));
    Query.AddIgnoredActor(Pawn);
    TestFalse(TEXT("Seated crew exclusions still apply to the expanded envelope"),
        WarSiegeEquipment::MovementContacts(World,HullCenter,FQuat::Identity,Vehicle->Definition->HullExtent,Query,Recovery));
    Query.ClearIgnoredActors();Query.AddIgnoredActor(Vehicle);
    Pawn->SetActorLocation(FVector(196,350,98.15));
    TestTrue(TEXT("A clear flank still permits the complete movement sweep"),
        Vehicle->MovementClear(FVector::ZeroVector,FRotator::ZeroRotator));
    TestFalse(TEXT("A clear flank does not trigger displacement or temporary collision ignores"),
        WarSiegeEquipment::MovementContacts(World,HullCenter,FQuat::Identity,Vehicle->Definition->HullExtent,Query,Recovery));
    auto* Controller=World->SpawnActor<AWarPlayerController>();
    auto* State=World->SpawnActor<AWarPlayerState>();Controller->PlayerState=State;State->SetOwner(Controller);
    Controller->Possess(Pawn);
    auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();Vehicle->SetOwner(Encounter);
    TestFalse(TEXT("An overlapping nonparticipant cannot be relocated"),Vehicle->CanRecoverCharacter(Pawn));
    State->SetSiegeMembership(Encounter);
    TestTrue(TEXT("This encounter's own character can recover"),Vehicle->CanRecoverCharacter(Pawn));
    auto* Other=World->SpawnActor<AWarSiegeEncounter>();State->SetSiegeMembership(Other);
    TestFalse(TEXT("Another encounter's participant cannot be relocated"),Vehicle->CanRecoverCharacter(Pawn));
    Vehicle->SetOwner(nullptr);
    TestFalse(TEXT("Unowned equipment cannot relocate characters"),Vehicle->CanRecoverCharacter(Pawn));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeProjectedRouteStartTest,"AegisWar.Foundation.SiegeProjectedRouteStart",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSiegeProjectedRouteStartTest::RunTest(const FString& Parameters)
{
    // The first point is the observed 270.6-second support projection. The
    // onward point is synthetic: that receipt did not record the second point.
    const FVector Position(7918.904682003663,-3863.448653978244,1678.0714111328125);
    const FVector Projection(7904,-3863.448653978244,1692.3302985795199);
    const TArray<FVector> Route={Projection,Position+FVector(0,250,100)};
    TestEqual(TEXT("A nearby initial projection may be bypassed only after a clear convoy ray"),
        WarSiegeEquipment::RouteStartIndex(Position,Route,true),1);
    TestEqual(TEXT("A blocked or unverified onward chord retains the initial point"),
        WarSiegeEquipment::RouteStartIndex(Position,Route,false),0);
    TestEqual(TEXT("The diagnostic projection would otherwise demand a reverse turn"),
        (Projection-Position).GetSafeNormal2D().Rotation().Yaw,180.);
    TestEqual(TEXT("A single terminal point is never discarded"),
        WarSiegeEquipment::RouteStartIndex(Position,TArray<FVector>{Projection},true),0);
    TestEqual(TEXT("An empty path is never indexed"),WarSiegeEquipment::RouteStartIndex(Position,{},true),0);
    TestEqual(TEXT("Already reached starts use the existing arrival rule without a new skip"),
        WarSiegeEquipment::RouteStartIndex(FVector::ZeroVector,TArray<FVector>{FVector(4.99,0,0),FVector(100,0,0)},true),0);
    TestEqual(TEXT("The bounded projection tolerance includes twenty centimetres"),
        WarSiegeEquipment::RouteStartIndex(FVector::ZeroVector,TArray<FVector>{FVector(-20,0,0),FVector(100,0,0)},true),1);
    TestEqual(TEXT("A larger projection offset must be visited"),
        WarSiegeEquipment::RouteStartIndex(FVector::ZeroVector,TArray<FVector>{FVector(-20.01,0,0),FVector(100,0,0)},true),0);
    const FVector Invalid(NAN,0,0);
    TestEqual(TEXT("An invalid position fails closed"),WarSiegeEquipment::RouteStartIndex(Invalid,Route,true),0);
    TestEqual(TEXT("An invalid first point fails closed"),
        WarSiegeEquipment::RouteStartIndex(Position,TArray<FVector>{Invalid,Projection},true),0);
    TestEqual(TEXT("An invalid onward point fails closed"),
        WarSiegeEquipment::RouteStartIndex(Position,TArray<FVector>{Projection,Invalid},true),0);

    TArray<FVector> Corner={FVector(-14.9,0,0),FVector(0,6,0),FVector(400,6,0)};
    Corner.RemoveAt(0,WarSiegeEquipment::RouteStartIndex(FVector::ZeroVector,Corner,true));
    TestEqual(TEXT("Only the initial projection is removed"),Corner.Num(),2);
    TestTrue(TEXT("A nearby real corner remains the steering target"),Corner[0].Equals(FVector(0,6,0)));
    TestTrue(TEXT("The unchanged five-centimetre corner arrival check cannot skip it"),FVector::Dist2D(FVector::ZeroVector,Corner[0])>=5);
    for (int32 Replan=0;Replan<20;++Replan)
    {
        const FVector Current(Replan*100,0,0);
        const TArray<FVector> Fresh={Current-FVector(14.9,0,0),Current+FVector(250,0,0)};
        const int32 Target=WarSiegeEquipment::RouteStartIndex(Current,Fresh,true);
        TestTrue(TEXT("Repeated moving-goal replans retain forward steering"),(Fresh[Target]-Current).GetSafeNormal2D().X>0);
    }

    // Navigation permission never replaces the real physical hull sweep.
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Vehicle=World->SpawnActor<AWarSiegeEquipment>();
    Vehicle->Definition=NewObject<UWarSiegeEquipmentDefinition>();Vehicle->Definition->HullExtent=FVector(245,178,120);
    auto* Obstacle=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Obstacle);
    Obstacle->SetRootComponent(Box);Box->SetBoxExtent(FVector(100,20,140));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionObjectType(ECC_WorldStatic);
    Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();
    Obstacle->SetActorLocation(FVector(0,240,155));
    TestTrue(TEXT("The chassis begins clear of the wall"),Vehicle->MovementClear(FVector::ZeroVector,FRotator::ZeroRotator));
    TestFalse(TEXT("A permitted onward target still cannot sweep its hull through the wall"),
        Vehicle->MovementClear(FVector(0,80,0),FRotator::ZeroRotator));
    return !HasAnyErrors();
}
#endif
