#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarLandscapeDetail.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarLandscapeDetailTest,"AegisWar.Foundation.LandscapeDetail",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarLandscapeDetailTest::RunTest(const FString& Parameters)
{
    const auto Values=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    if(!TestNotNull(TEXT("Detail test world"),World))return false;
    auto* Actor=World->SpawnActor<AWarLandscapeDetail>();
    // A test-only mesh exercises admission atomically; production clusters require their reviewed source model.
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    const TArray<FTransform> Valid={FTransform(FRotator(0,31,0),FVector(120,240,30),FVector(.6))};
    TestFalse(TEXT("Missing model never substitutes a visual"),Actor->Configure(nullptr,Valid));
    TestTrue(TEXT("Valid source-model batch admitted"),Actor->Configure(Mesh,Valid));
    TestFalse(TEXT("Cosmetics never block movement"),Actor->Details->GetCollisionEnabled()!=ECollisionEnabled::NoCollision);
    TestFalse(TEXT("Cosmetics never change navigation"),Actor->Details->CanEverAffectNavigation());
    TestFalse(TEXT("Cosmetic transforms are not replicated"),Actor->GetIsReplicated());
    TestFalse(TEXT("Empty batch rejected"),Actor->Configure(Mesh,{}));
    TestFalse(TEXT("Out-of-envelope batch rejected"),Actor->Configure(Mesh,{FTransform(FVector(300000,0,0))}));
    TestFalse(TEXT("Oversized instance rejected"),Actor->Configure(Mesh,{FTransform(FQuat::Identity,FVector::ZeroVector,FVector(3))}));
    TestEqual(TEXT("Rejected batches preserve the previous cluster"),Actor->Details->GetInstanceCount(),1);
    FTransform Actual;Actor->Details->GetInstanceTransform(0,Actual);
    TestTrue(TEXT("Admitted transform retained"),Actual.Equals(Valid[0],.001));
    World->DestroyWorld(false);return true;
}
#endif
