#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarDutchBastionProof.h"
#include "WarCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelRouteWidthTest,"AegisWar.Foundation.CitadelRouteWidth",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelRouteWidthTest::RunTest(const FString& Parameters)
{
    const FVector From(0,0,0),To(250,0,60); FVector Seed;double Offset=0;
    TestEqual(TEXT("Non-multiple segments retain spacing below 100 cm"),WarCitadelRouteWidth::Intervals(From,To),3);
    TestTrue(TEXT("Outer capsule center fits precisely inside the signed edge"),
        WarCitadelRouteWidth::Sample(From,To,600,42,3,1,Seed,Offset));
    TestEqual(TEXT("Capsule-constrained edge has no width relaxation"),Offset,258.);
    TestEqual(TEXT("Endpoint and elevation interpolation remain signed"),Seed,FVector(250,258,60));
    TestTrue(TEXT("Half lane is sampled independently"),WarCitadelRouteWidth::Sample(From,To,600,42,1,-.5,Seed,Offset));
    TestTrue(TEXT("Half lane uses normalized XY perpendicular"),Seed.Equals(FVector(250./3,-129,20),.0001));
    TestFalse(TEXT("Vertical-only geometry cannot masquerade as a walking route"),
        WarCitadelRouteWidth::Sample(From,FVector(0,0,60),600,42,0,0,Seed,Offset));
    TestFalse(TEXT("A smaller-than-capsule width is rejected"),WarCitadelRouteWidth::Sample(From,To,84,42,0,0,Seed,Offset));
    TestFalse(TEXT("Unconfigured lateral lanes are rejected"),WarCitadelRouteWidth::Sample(From,To,600,42,0,.75,Seed,Offset));
    TestTrue(TEXT("Retained ramp seeds use the signed slope without moving the anchor"),
        WarCitadelRouteWidth::SpawnPadSeed(FVector(5800,-4800,910),600,42,0,-2,2,FVector2D(.5,0),Seed));
    TestEqual(TEXT("Actual 1:2 ramp footprint follows uphill height"),Seed,FVector(5542,-4542,781));
    TestFalse(TEXT("Upper pads cannot acquire an invented slope"),
        WarCitadelRouteWidth::SpawnPadSeed(From,600,42,2,0,0,FVector2D(.5,0),Seed));
    TestFalse(TEXT("The footprint cannot relax walkable slope"),
        WarCitadelRouteWidth::SpawnPadSeed(From,600,42,0,0,0,FVector2D(2,0),Seed));
    TestFalse(TEXT("Only the exact signed 5-by-5 grid is accepted"),
        WarCitadelRouteWidth::SpawnPadSeed(From,600,42,0,3,0,FVector2D::ZeroVector,Seed));

    auto Profile=MakeShared<FJsonObject>();
    Profile->SetNumberField(TEXT("schemaVersion"),1);Profile->SetStringField(TEXT("routeId"),TEXT("fan"));
    Profile->SetStringField(TEXT("kind"),TEXT("world_x_piecewise_linear"));
    Profile->SetStringField(TEXT("meshId"),TEXT("stairs_and_balconies"));
    Profile->SetStringField(TEXT("boundaryPolicy"),TEXT("closed_profile_domain_shared_boundaries_same_height"));
    Profile->SetStringField(TEXT("construction"),TEXT("continuous_paved_fan_ramp"));
    const auto Knot=[](double X,double Z)
    { return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(X),MakeShared<FJsonValueNumber>(Z)}); };
    Profile->SetArrayField(TEXT("knotsCm"),{Knot(-1000,0),Knot(0,0),Knot(100,100),Knot(1000,100)});
    WarCitadelRouteWidth::FSurface Surface;double Z=0;
    TestTrue(TEXT("Signed finite fan surface validates in forward direction"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("fan:forward"),Surface));
    TestTrue(TEXT("Reverse traversal uses the identical world surface"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("fan:reverse"),Surface));
    TestFalse(TEXT("A profile cannot be attached to another corridor"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("other:forward"),Surface));
    TestTrue(TEXT("Surface can be read after a rejected identity"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("fan:forward"),Surface));
    TestTrue(TEXT("Movement substeps evaluate inside each height interval"),WarCitadelRouteWidth::Height(Surface,50,Z));
    TestEqual(TEXT("Height follows the authored surface rather than endpoint interpolation"),Z,50.);
    TestTrue(TEXT("The closed knot boundary retains its exact height"),WarCitadelRouteWidth::Height(Surface,100,Z));
    TestEqual(TEXT("Shared knot seams are continuous"),Z,100.);
    TestFalse(TEXT("Surface height is never extrapolated outside the signed domain"),WarCitadelRouteWidth::Height(Surface,1000.01,Z));
    TestFalse(TEXT("Even a tiny domain escape is rejected identically by the samplers"),WarCitadelRouteWidth::Height(Surface,1000.0000001,Z));
    TestTrue(TEXT("Outer curved lane retains its full width and authored cross-slope"),
        WarCitadelRouteWidth::Sample(FVector(0,0,0),FVector(250,250,100),600,42,0,-1,Seed,Offset,&Surface));
    TestEqual(TEXT("Cross-slope seed follows its actual world X"),Seed.Z,100.);
    TestEqual(TEXT("A fan profile does not reduce capsule edge clearance"),Offset,-258.);
    Profile->SetStringField(TEXT("schemaVersion"),TEXT("1"));
    TestFalse(TEXT("JSON string numerics cannot impersonate the signed profile version"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("fan:forward"),Surface));
    Profile->SetNumberField(TEXT("schemaVersion"),1);
    Profile->SetArrayField(TEXT("knotsCm"),{MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
        MakeShared<FJsonValueString>(TEXT("0")),MakeShared<FJsonValueNumber>(0)}),Knot(100,100)});
    TestFalse(TEXT("JSON knot coordinates require actual numbers"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("fan:forward"),Surface));
    Profile->SetArrayField(TEXT("knotsCm"),{Knot(0,0),Knot(100,150)});
    TestFalse(TEXT("Fan surfaces cannot relax the native walkable slope"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("fan:forward"),Surface));
    Profile->SetArrayField(TEXT("knotsCm"),{Knot(100,0),Knot(0,0)});
    TestFalse(TEXT("Ambiguous or reversed knot domains are rejected"),WarCitadelRouteWidth::ReadSurface(Profile,TEXT("fan:forward"),Surface));

    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());World->BeginPlay();World->GetWorldSettings()->NotifyBeginPlay();
    const auto Box=[&](const FVector& Position,const FVector& Extent)
    {
        auto* Actor=World->SpawnActor<AActor>();auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->SetRootComponent(Shape);Shape->SetBoxExtent(Extent);Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Shape->SetCollisionObjectType(ECC_WorldStatic);Shape->SetCollisionResponseToAllChannels(ECR_Block);
        Shape->RegisterComponent();Actor->SetActorLocation(Position);return Actor;
    };
    auto* BaseFloor=Box(FVector(0,0,-10),FVector(3000,3000,10));
    Cast<UBoxComponent>(BaseFloor->GetRootComponent())->SetMobility(EComponentMobility::Static);
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Pawn=World->SpawnActor<AWarCharacter>(FVector(-500,-500,98.4),FRotator::ZeroRotator,Spawn);
    Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    const FVector Original=Pawn->GetActorLocation();
    TestTrue(TEXT("Actual full-size capsule has grounded flat placement"),WarCitadelRouteWidth::Ground(Pawn,From).Clear);
    Box(FVector(150,0,10),FVector(100,200,10));
    TestTrue(TEXT("A normal stair tread has a clear native resting pose"),WarCitadelRouteWidth::Ground(Pawn,FVector(100,0,20)).Clear);
    const auto Stair=WarCitadelRouteWidth::Traverse(Pawn,From,FVector(250,0,20));
    TestTrue(TEXT("Movement-sized native sweeps accept an ordinary step"),Stair.Clear);
    TestTrue(TEXT("100 cm evidence spacing is subdivided for actual stair movement"),Stair.MovementSteps>=25);
    Box(FVector(650,0,40),FVector(100,200,40));
    TestFalse(TEXT("Ground samples cannot lift ordinary walking over an 80 cm wall"),
        WarCitadelRouteWidth::Traverse(Pawn,FVector(450,0,0),FVector(700,0,80)).Clear);
    Surface.KnotsCm={FVector2D(450,0),FVector2D(700,80)};
    TestFalse(TEXT("An authored floor profile cannot carry the real capsule over an 80 cm wall"),
        WarCitadelRouteWidth::Traverse(Pawn,FVector(450,0,0),FVector(700,0,80),&Surface).Clear);
    const double RampSlope=.3,Pitch=FMath::RadiansToDegrees(FMath::Atan(RampSlope));
    auto* Ramp=Box(FVector(0,1500,-10*FMath::Sqrt(1+RampSlope*RampSlope)),FVector(600,300,10));
    Ramp->SetActorRotation(FRotator(Pitch,0,0));
    Surface.KnotsCm={FVector2D(-500,-150),FVector2D(500,150)};
    const auto Fan=WarCitadelRouteWidth::Traverse(Pawn,FVector(100,1400,30),FVector(400,1600,120),&Surface);
    TestTrue(TEXT("A signed cross-slope uses actual grounded native movement on its continuous ramp"),Fan.Clear);
    TestTrue(TEXT("Every fan movement step retains the physical 10 cm spacing"),Fan.MovementSteps>=37);
    Pawn->GetCharacterMovement()->bMaintainHorizontalGroundVelocity=false;
    TestTrue(TEXT("Native ramp projection respects non-horizontal speed policy"),
        WarCitadelRouteWidth::Traverse(Pawn,FVector(100,1400,30),FVector(400,1600,120),&Surface).Clear);
    Pawn->GetCharacterMovement()->bMaintainHorizontalGroundVelocity=true;
    TestFalse(TEXT("The signed fan domain cannot be extrapolated during movement"),
        WarCitadelRouteWidth::Traverse(Pawn,FVector(100,1400,30),FVector(501,1600,150.3),&Surface).Clear);
    auto* Ceiling=Box(FVector(100,500,180),FVector(300,150,10));
    const auto Headroom=WarCitadelRouteWidth::Ground(Pawn,FVector(100,500,0));
    TestFalse(TEXT("Low headroom rejects a full capsule even with a valid floor"),Headroom.Clear);
    TestTrue(TEXT("Blocked headroom retains the full actual actor identity"),Headroom.HitActor==Ceiling->GetPathName());
    TestTrue(TEXT("Blocked placement records the actual failing pose"),Headroom.Diagnostic.IsValid());
    const auto ClearContacts=WarCitadelRouteWidth::CapsuleContactDiagnostic(Pawn,FVector(-500,-500,98.4));
    TestTrue(TEXT("Matched collision controls execute in the actual game world"),
        ClearContacts.IsValid() && ClearContacts->GetBoolField(TEXT("diagnosticOnly"))
        && ClearContacts->GetNumberField(TEXT("worldType"))==int32(EWorldType::Game));
    TestFalse(TEXT("Clear full-capsule floor is a negative overlap control"),
        ClearContacts->GetObjectField(TEXT("admissionQuery"))->GetBoolField(TEXT("overlapBlocking")));
    TestEqual(TEXT("Contact diagnostics retain the actual full capsule radius"),ClearContacts->GetNumberField(TEXT("radiusCm")),42.);
    TestEqual(TEXT("Contact diagnostics retain the actual full capsule height"),ClearContacts->GetNumberField(TEXT("halfHeightCm")),96.);
    for (const FVector Center:{FVector(100,500,98.4),FVector(650,0,98.4)})
    {
        const auto Contacts=WarCitadelRouteWidth::CapsuleContactDiagnostic(Pawn,Center);
        const auto& Admission=Contacts->GetObjectField(TEXT("admissionQuery"));
        TestTrue(TEXT("Ceiling and wall remain positive blocking overlap controls"),Admission->GetBoolField(TEXT("overlapBlocking")));
        const auto& Sweeps=Admission->GetArrayField(TEXT("matchedSweeps"));
        TestEqual(TEXT("Exact zero, positive and negative Z sweeps are all recorded"),Sweeps.Num(),3);
        for (const auto& Sweep:Sweeps)
            TestTrue(TEXT("Matched native box sweeps retain initial obstruction"),Sweep->AsObject()->GetBoolField(TEXT("singleBlocking")));
        TestTrue(TEXT("All overlap component identities are retained"),Admission->GetArrayField(TEXT("overlaps")).Num()>0);
        bool DirectPositive=false;
        for (const auto& Value:Admission->GetArrayField(TEXT("overlaps")))
        {
            const auto& Overlap=Value->AsObject();if (!Overlap->GetBoolField(TEXT("blocking"))) continue;
            const auto& Direct=Overlap->GetObjectField(TEXT("directBodyQuery"));
            const auto& Cooked=Direct->GetObjectField(TEXT("cookedTriangleWitness"));
            TestTrue(TEXT("Actual live body geometry is read under its physics lock"),
                Cooked->GetBoolField(TEXT("diagnosticOnly")) && Cooked->GetBoolField(TEXT("readLockEntered"))
                && Cooked->GetNumberField(TEXT("selectedShapeCount"))>0);
            TestFalse(TEXT("A simple box cannot masquerade as a complete cooked triangle witness"),Cooked->GetBoolField(TEXT("complete")));
            DirectPositive|=Direct->GetBoolField(TEXT("withoutMTD")) && Direct->GetBoolField(TEXT("withMTD"))
                && Direct->GetNumberField(TEXT("mtdDistanceCm"))>0;
        }
        TestTrue(TEXT("Direct blocking-body controls retain actual penetration with and without MTD"),DirectPositive);
    }
    Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(Ceiling,true);
    const auto IgnoreComparison=WarCitadelRouteWidth::CapsuleContactDiagnostic(Pawn,FVector(100,500,98.4));
    TestTrue(TEXT("Movement ignore differences never waive the original admission overlap"),
        IgnoreComparison->GetObjectField(TEXT("admissionQuery"))->GetBoolField(TEXT("overlapBlocking")));
    TestFalse(TEXT("Movement query comparison records its actual separate ignore semantics"),
        IgnoreComparison->GetObjectField(TEXT("movementQueryComparison"))->GetBoolField(TEXT("overlapBlocking")));
    TestEqual(TEXT("Actual movement ignore actor identity is disclosed"),IgnoreComparison->GetArrayField(TEXT("moveIgnoreActors"))[0]->AsString(),Ceiling->GetPathName());
    Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(Ceiling,false);
    TestEqual(TEXT("Contact queries never move the pawn"),Pawn->GetActorLocation(),Original);
    Box(FVector(200,-1500,-3.5),FVector(200,300,10));
    const auto Seam=WarCitadelRouteWidth::Ground(Pawn,FVector(0,-1500,6.5));
    TestTrue(TEXT("A 6.5 cm seam retains the native full-capsule support handoff"),Seam.Clear);
    TestTrue(TEXT("Native walking traverses the seam uphill"),
        WarCitadelRouteWidth::Traverse(Pawn,FVector(-100,-1500,0),FVector(100,-1500,6.5)).Clear);
    TestTrue(TEXT("Native walking traverses the seam downhill"),
        WarCitadelRouteWidth::Traverse(Pawn,FVector(100,-1500,6.5),FVector(-100,-1500,0)).Clear);
    auto* Movement=Pawn->GetCharacterMovement();
    const auto Rest=WarCitadelRouteWidth::Ground(Pawn,FVector(-100,-1500,0));
    Pawn->SetActorLocation(Rest.Center,false,nullptr,ETeleportType::TeleportPhysics);
    Movement->FindFloor(Rest.Center,Movement->CurrentFloor,false);
    Movement->bRunPhysicsWithNoController=true;Movement->GroundFriction=0;Movement->BrakingDecelerationWalking=0;
    for (int32 I=0;I<20;++I)
    {
        Movement->Velocity=FVector(200,0,0);
        Movement->StartNewPhysics(.05,0);
    }
    TestTrue(TEXT("The same seam is playable using the engine MoveAlongFloor routine"),
        FMath::Abs(Pawn->GetActorLocation().X-100)<1 && FMath::Abs(Pawn->GetActorLocation().Y+1500)<1
        && FMath::Abs(Pawn->GetActorLocation().Z-(6.5+96+Movement->CurrentFloor.GetDistanceToFloor()))<.1
        && Movement->CurrentFloor.IsWalkableFloor() && !Movement->CurrentFloor.HitResult.bStartPenetrating);
    for (int32 I=0;I<20;++I)
    { Movement->Velocity=FVector(-200,0,0);Movement->StartNewPhysics(.05,0); }
    FCollisionQueryParams Clearance(SCENE_QUERY_STAT(CitadelSeamFixture),false,Pawn);
    TestTrue(TEXT("Real native downhill physics retains floor, endpoint and full headroom"),
        FMath::Abs(Pawn->GetActorLocation().X+100)<1 && FMath::Abs(Pawn->GetActorLocation().Y+1500)<1
        && FMath::Abs(Pawn->GetActorLocation().Z-(96+Movement->CurrentFloor.GetDistanceToFloor()))<.1
        && Movement->CurrentFloor.IsWalkableFloor() && !Movement->CurrentFloor.HitResult.bStartPenetrating
        && !World->OverlapBlockingTestByChannel(Pawn->GetActorLocation(),FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeCapsule(42,96),Clearance));
    Pawn->SetActorLocation(Original,false,nullptr,ETeleportType::TeleportPhysics);
    auto* Base=Cast<UPrimitiveComponent>(Ceiling->GetRootComponent());
    Movement->SetMovementMode(MOVE_Falling);Pawn->SetBase(Base);
    Pawn->bPressedJump=true;Pawn->bWasJumping=true;Pawn->JumpKeyHoldTime=.7;Pawn->JumpCurrentCount=1;
    TestFalse(TEXT("Falling callers are rejected before changing jump or movement state"),WarCitadelRouteWidth::Ground(Pawn,From).Clear);
    TestTrue(TEXT("Rejected caller retains its movement base"),Pawn->GetMovementBase()==Base);
    TestEqual(TEXT("Rejected caller retains its movement mode"),Movement->MovementMode,MOVE_Falling);
    TestTrue(TEXT("Rejected caller retains jump flags"),Pawn->bPressedJump && Pawn->bWasJumping);
    TestEqual(TEXT("Rejected caller retains jump hold time"),Pawn->JumpKeyHoldTime,.7f);
    TestEqual(TEXT("Rejected caller retains jump count"),Pawn->JumpCurrentCount,1);
    Movement->SetMovementMode(MOVE_Walking);Pawn->SetBase(static_cast<UPrimitiveComponent*>(nullptr));
    auto* Lip=Box(FVector(60,-2200,3.25),FVector(40,100,3.25));
    auto* LipShape=Cast<UBoxComponent>(Lip->GetRootComponent());
    LipShape->SetMobility(EComponentMobility::Static);
    LipShape->SetWalkableSlopeOverride(FWalkableSlopeOverride(WalkableSlope_Unwalkable,0));
    const FVector LineCenter(0,-2200,100);
    Pawn->SetActorLocation(LineCenter,false,nullptr,ETeleportType::TeleportPhysics);
    Movement->FindFloor(LineCenter,Movement->CurrentFloor,false);
    const auto BeforeLine=Movement->CurrentFloor;
    TestTrue(TEXT("Unwalkable lip fixture actually enters the native line-fallback branch"),
        BeforeLine.bLineTrace && BeforeLine.IsWalkableFloor() && BeforeLine.FloorDist>UCharacterMovementComponent::MIN_FLOOR_DIST);
    TestTrue(TEXT("Line-fallback stores the center-line distance before adjustment"),FMath::Abs(BeforeLine.LineDist-4)<.1);
    Movement->AdjustFloorHeight();
    const auto VerifiedLine=WarCitadelRouteWidth::AdjustedSupport(Pawn,BeforeLine,LineCenter,
        Movement->CurrentFloor,Pawn->GetActorLocation());
    TestTrue(TEXT("Actual swept adjustment changes the pose while the cache stays stale"),
        Pawn->GetActorLocation().Z<99 && Movement->CurrentFloor.bLineTrace && FMath::Abs(Movement->CurrentFloor.LineDist-4)<.1);
    TestTrue(TEXT("Independent native center-line support verifies actual 2.15 cm clearance"),
        VerifiedLine.Verified && FMath::Abs(VerifiedLine.Distance-2.15)<.1 && VerifiedLine.Diagnostic.IsValid());
    TestFalse(TEXT("Line verification cannot accept a larger actual floor gap"),
        WarCitadelRouteWidth::AdjustedSupport(Pawn,BeforeLine,LineCenter,Movement->CurrentFloor,LineCenter).Verified);
    TestFalse(TEXT("Line verification cannot reinterpret a synthetic perch distance"),
        WarCitadelRouteWidth::AdjustedSupport(Pawn,BeforeLine,LineCenter+FVector(0,0,1),Movement->CurrentFloor,Pawn->GetActorLocation()).Verified);
    TestTrue(TEXT("Line-supported native pose still fits the entire capsule"),
        !World->OverlapBlockingTestByChannel(Pawn->GetActorLocation(),FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeCapsule(42,96),Clearance));
    Pawn->SetActorLocation(Original,false,nullptr,ETeleportType::TeleportPhysics);
    Movement->Velocity=FVector(31,-7,0);Movement->bJustTeleported=false;Movement->bForceNextFloorCheck=true;
    const auto SavedFloor=Movement->CurrentFloor;
    WarCitadelRouteWidth::Ground(Pawn,From);
    WarCitadelRouteWidth::Traverse(Pawn,FVector(450,0,0),FVector(700,0,80));
    TestEqual(TEXT("Clear placement and failed transition preserve velocity"),Movement->Velocity,FVector(31,-7,0));
    TestTrue(TEXT("Clear placement and failed transition preserve native floor flags"),
        !Movement->bJustTeleported && Movement->bForceNextFloorCheck
        && Movement->CurrentFloor.FloorDist==SavedFloor.FloorDist
        && Movement->CurrentFloor.HitResult.GetActor()==SavedFloor.HitResult.GetActor());
    TestFalse(TEXT("Missing floor is never filled by a route's expected elevation"),WarCitadelRouteWidth::Ground(Pawn,FVector(4000,0,0)).Clear);
    TestEqual(TEXT("Physical fixtures restore the original playable pawn position"),Pawn->GetActorLocation(),Original);
    World->EndPlay(EEndPlayReason::Quit);GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
    return !HasAnyErrors();
}
#endif
