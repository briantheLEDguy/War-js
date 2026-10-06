#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCitadelCapsulePolicy.h"
#include "WarDutchBastionProof.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "GameFramework/CharacterMovementComponent.h"
#include <cmath>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelCapsulePolicyTest,"AegisWar.Foundation.CitadelCapsulePolicy",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelCapsulePolicyTest::RunTest(const FString& Parameters)
{
    const auto* Default=GetDefault<AWarCharacter>();
    const auto* DefaultCapsule=Default->GetCapsuleComponent();const auto* DefaultMovement=Default->GetCharacterMovement();
    AddInfo(FString::Printf(TEXT("Native default capsule: scaled %.9g/%.9g unscaled %.9g/%.9g scale %s axis %s step %.9g slope %.9g gravity %.9g direction %s updatedCapsule %d"),
        DefaultCapsule->GetScaledCapsuleRadius(),DefaultCapsule->GetScaledCapsuleHalfHeight(),DefaultCapsule->GetUnscaledCapsuleRadius(),
        DefaultCapsule->GetUnscaledCapsuleHalfHeight(),*DefaultCapsule->GetComponentScale().ToString(),*DefaultCapsule->GetComponentQuat().GetUpVector().ToString(),
        DefaultMovement->MaxStepHeight,DefaultMovement->GetWalkableFloorZ(),DefaultMovement->GravityScale,*DefaultMovement->GetGravityDirection().ToString(),
        DefaultMovement->UpdatedComponent==DefaultCapsule));
    TestTrue(TEXT("Unmodified native default retains its reviewed visibility and gizmo responses"),
        WarCitadelCapsulePolicy::Matches(Default));
    const auto DefaultBefore=Default->GetCapsuleComponent()->GetCollisionResponseToChannels();
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());World->BeginPlay();World->GetWorldSettings()->NotifyBeginPlay();
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Pawn=World->SpawnActor<AWarCharacter>(FVector(0,0,100),FRotator::ZeroRotator,Spawn);
    if (!Pawn) { World->EndPlay(EEndPlayReason::Quit);GEngine->DestroyWorldContext(World);World->DestroyWorld(false);return false; }
    auto* Capsule=Pawn->GetCapsuleComponent();Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    const auto* SpawnMovement=Pawn->GetCharacterMovement();
    AddInfo(FString::Printf(TEXT("Spawned capsule: scaled %.9g/%.9g unscaled %.9g/%.9g scale %s axis %s step %.9g slope %.9g gravity %.9g direction %s updatedCapsule %d"),
        Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight(),Capsule->GetUnscaledCapsuleRadius(),Capsule->GetUnscaledCapsuleHalfHeight(),
        *Capsule->GetComponentScale().ToString(),*Capsule->GetComponentQuat().GetUpVector().ToString(),SpawnMovement->MaxStepHeight,
        SpawnMovement->GetWalkableFloorZ(),SpawnMovement->GravityScale,*SpawnMovement->GetGravityDirection().ToString(),SpawnMovement->UpdatedComponent==Capsule));
    TestTrue(TEXT("Actual spawned character matches its class default without replacing collision"),WarCitadelCapsulePolicy::Matches(Pawn));
    const WarCitadelCapsulePolicy::FKinematicsBaseline Captured(Pawn);
    const float CapturedFloor=SpawnMovement->GetWalkableFloorZ(),NativeFloor=DefaultMovement->GetWalkableFloorZ();
    Pawn->GetCharacterMovement()->SetWalkableFloorZ(CapturedFloor==NativeFloor ? std::nextafter(CapturedFloor,1.f) : NativeFloor);
    TestTrue(TEXT("Native spawn's one-ULP slope difference is a valid initialization"),WarCitadelCapsulePolicy::Matches(Pawn));
    TestFalse(TEXT("Even a valid one-ULP change after capture fails the pinned runtime baseline"),Captured.Matches(Pawn));
    Pawn->GetCharacterMovement()->SetWalkableFloorZ(CapturedFloor);
    TestTrue(TEXT("Restoring the recorded runtime value restores baseline agreement"),Captured.Matches(Pawn));
    const auto Receipt=WarCitadelCapsulePolicy::Readback(Pawn);
    TestEqual(TEXT("Actual receipt exports all 64 supported response slots"),Receipt->GetArrayField(TEXT("responses")).Num(),64);
    TestEqual(TEXT("Default receipt exports the same full container"),Receipt->GetArrayField(TEXT("classDefaultResponses")).Num(),64);
    TestEqual(TEXT("Visibility override is recorded honestly as Custom"),Receipt->GetStringField(TEXT("profile")),FString(TEXT("Custom")));
    for (int32 I=0;I<UE_ARRAY_COUNT(DefaultBefore.EnumArray);++I)
    {
        const auto Channel=ECollisionChannel(I);
        Capsule->SetCollisionResponseToChannel(Channel,DefaultBefore.EnumArray[I]==ECR_Ignore ? ECR_Block : ECR_Ignore);
        TestFalse(TEXT("Each independently altered response fails the live check"),WarCitadelCapsulePolicy::Matches(Pawn));
        TestFalse(TEXT("A changed response cannot authorize a route placement"),WarCitadelRouteWidth::Ground(Pawn,FVector::ZeroVector).Clear);
        TestEqual(TEXT("Placement fails before querying a missing floor"),WarCitadelRouteWidth::Ground(Pawn,FVector::ZeroVector).Reason,
            FString(TEXT("native pawn capsule collision is unavailable")));
        Capsule->SetCollisionResponseToChannel(Channel,ECollisionResponse(DefaultBefore.EnumArray[I]));
        TestTrue(TEXT("Restoring the native response restores policy eligibility"),WarCitadelCapsulePolicy::Matches(Pawn));
    }
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    TestFalse(TEXT("Query-only capsules cannot claim unchanged character physics"),WarCitadelCapsulePolicy::Matches(Pawn));
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Capsule->SetCollisionObjectType(ECC_WorldDynamic);
    TestFalse(TEXT("Another query object channel cannot claim Pawn policy"),WarCitadelCapsulePolicy::Matches(Pawn));
    Capsule->SetCollisionObjectType(ECC_Pawn);
    Pawn->SetActorEnableCollision(false);
    TestFalse(TEXT("Actor-level collision suspension also fails closed"),WarCitadelCapsulePolicy::Matches(Pawn));
    Pawn->SetActorEnableCollision(true);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));
    TestFalse(TEXT("Relabelling the character as Pawn discards its required visibility override"),WarCitadelCapsulePolicy::Matches(Pawn));
    Capsule->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    TestTrue(TEXT("The actual native constructor policy is recovered"),WarCitadelCapsulePolicy::Matches(Pawn));
    const auto GeometryReceipt=WarCitadelCapsulePolicy::KinematicsReadback(Pawn);
    Capsule->SetCapsuleSize(21.f,48.f);
    TestFalse(TEXT("Shrinking after receipt capture is rejected on the next live query"),WarCitadelCapsulePolicy::Matches(Pawn));
    TestFalse(TEXT("The captured receipt cannot authorize a smaller physical placement"),WarCitadelRouteWidth::Ground(Pawn,FVector::ZeroVector).Clear);
    TestEqual(TEXT("Captured dimensions do not silently follow a changed body"),GeometryReceipt->GetNumberField(TEXT("scaledRadiusCm")),42.);
    Capsule->SetCapsuleSize(42.f,96.f);
    auto* Movement=Pawn->GetCharacterMovement();Movement->MaxStepHeight=90.f;
    TestFalse(TEXT("Increasing step height after capture cannot clear a higher obstacle"),WarCitadelCapsulePolicy::Matches(Pawn));
    Movement->MaxStepHeight=45.f;
    const float FloorZ=Movement->GetWalkableFloorZ();Movement->SetWalkableFloorZ(.2f);
    TestFalse(TEXT("Relaxing the walkable slope fails the live policy"),WarCitadelCapsulePolicy::Matches(Pawn));
    Movement->SetWalkableFloorZ(FloorZ);
    Movement->GravityScale=0.f;
    TestFalse(TEXT("Zero gravity cannot produce a walking receipt"),WarCitadelCapsulePolicy::Matches(Pawn));
    Movement->GravityScale=1.f;
    Capsule->SetWorldScale3D(FVector(.5));
    TestFalse(TEXT("Actor scaling cannot indirectly shrink the query hull"),WarCitadelCapsulePolicy::Matches(Pawn));
    Capsule->SetWorldScale3D(FVector::OneVector);
    Capsule->SetWorldRotation(FRotator(15,0,0));
    TestFalse(TEXT("A tilted capsule cannot use upright world-Z floor assumptions"),WarCitadelCapsulePolicy::Matches(Pawn));
    Capsule->SetWorldRotation(FRotator::ZeroRotator);
    Movement->SetUpdatedComponent(nullptr);
    TestFalse(TEXT("Another movement body cannot claim the recorded capsule"),WarCitadelCapsulePolicy::Matches(Pawn));
    Movement->SetUpdatedComponent(Capsule);
    TestTrue(TEXT("Restoring the native body and movement limits restores eligibility"),WarCitadelCapsulePolicy::Matches(Pawn));
    for (int32 I=0;I<UE_ARRAY_COUNT(DefaultBefore.EnumArray);++I)
        TestEqual(TEXT("Transient controls never alter the class default"),Default->GetCapsuleComponent()->GetCollisionResponseToChannels().EnumArray[I],DefaultBefore.EnumArray[I]);
    World->EndPlay(EEndPlayReason::Quit);GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
    return !HasAnyErrors();
}
#endif
