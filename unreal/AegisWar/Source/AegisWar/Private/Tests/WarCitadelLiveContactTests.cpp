#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCitadelCookedContacts.h"
#include "ProceduralMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/BodySetup.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "Dom/JsonObject.h"
#include "Engine/OverlapResult.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelLiveContactTest,"AegisWar.Foundation.CitadelLiveCookedContact",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelLiveContactTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());World->BeginPlay();World->GetWorldSettings()->NotifyBeginPlay();
    const FVector Center(12160,-5658,4254.425860524177);
    const auto MakeBody=[&](const TArray<FVector>& Vertices,const FTransform& Transform)
    {
        auto* Actor=World->SpawnActor<AActor>();auto* Mesh=NewObject<UProceduralMeshComponent>(Actor);Actor->SetRootComponent(Mesh);
        Mesh->SetMobility(EComponentMobility::Static);Mesh->SetHiddenInGame(true);
        Mesh->bUseAsyncCooking=false;Mesh->bUseComplexAsSimpleCollision=true;
        Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Mesh->SetCollisionObjectType(ECC_WorldStatic);
        Mesh->SetCollisionResponseToAllChannels(ECR_Block);
        TestTrue(TEXT("Fixture transform is established before static registration"),Actor->SetActorTransform(Transform));
        Mesh->RegisterComponent();
        TArray<int32> Indices;for (int32 I=0;I<Vertices.Num();++I) Indices.Add(I);
        Mesh->CreateMeshSection_LinearColor(0,Vertices,Indices,{},{},{},{},true);
        TestTrue(TEXT("Registered fixture retains the requested native transform"),Mesh->GetComponentTransform().Equals(Transform,1.e-8));
        return Mesh;
    };
    const auto Inspect=[&](UProceduralMeshComponent* Mesh,const FVector& At)
    {
        const auto* Body=Mesh->GetBodyInstance();
        TestTrue(TEXT("Temporary authored fixture has a real valid native physics body"),Body && Body->IsValidBodyInstance());
        return WarCitadelCookedContacts::Witness(Body,At,FQuat::Identity,42,96,false);
    };
    const TArray<FVector> Authored={{12200,-5700,4173.7001953125},{12300,-5081.818359375,4205.5},{12200,-5100,4173.7001953125}};
    auto* Separated=MakeBody(Authored,FTransform::Identity);auto Witness=Inspect(Separated,Center);
    TestTrue(TEXT("Authored live triangle geometry has complete read-locked witness coverage"),Witness->GetBoolField(TEXT("complete")));
    TestFalse(TEXT("Same-lock native penetration query retains the separated authored face"),Witness->GetBoolField(TEXT("sameReadLockMtdBlocking")));
    TestTrue(TEXT("Complete live body supports a diagnostic separation certificate"),Witness->GetBoolField(TEXT("separatedContactDiagnostic")));
    TestFalse(TEXT("The live diagnostic grants no admission"),Witness->GetBoolField(TEXT("admissionGranted")));
    const auto HitFor=[](UPrimitiveComponent* Component,int32 Item=INDEX_NONE)
    {
        FOverlapResult Hit;Hit.Component=Component;Hit.SetItemIndex(Item);Hit.bBlockingHit=true;return Hit;
    };
    const auto Resolve=[&](const TArray<FOverlapResult>& Hits)
    { return WarCitadelCookedContacts::ResolveOverlaps(Hits,Center,FQuat::Identity,42,96,false); };
    using Decision=WarCitadelCookedContacts::EContactDecision;
    TestTrue(TEXT("Fresh native separation is available to diagnostic all-body aggregation"),Resolve({HitFor(Separated)}).Decision==Decision::Separated);
    TArray<FOverlapResult> Raw;
    World->OverlapMultiByChannel(Raw,Center,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(42,96),FCollisionQueryParams());
    TestTrue(TEXT("Actual scene query reproduces the authored raw blocking contact"),Raw.ContainsByPredicate([&](const FOverlapResult& H)
        { return H.bBlockingHit && H.GetComponent()==Separated; }));
    TestTrue(TEXT("Actual raw scene hits are fully covered by the typed live diagnostic"),Resolve(Raw).Decision==Decision::Separated);

    const TArray<FVector> Wall={Center+FVector(20,-500,-500),Center+FVector(20,500,-500),Center+FVector(20,0,500)};
    auto* Blocking=MakeBody(Wall,FTransform::Identity);Witness=Inspect(Blocking,Center);
    TestTrue(TEXT("True wall has native same-lock penetration"),Witness->GetBoolField(TEXT("sameReadLockMtdBlocking")));
    TestFalse(TEXT("True wall cannot be certified separated"),Witness->GetBoolField(TEXT("separatedContactDiagnostic")));
    for (const auto& Hits:{TArray<FOverlapResult>{HitFor(Separated),HitFor(Blocking)},TArray<FOverlapResult>{HitFor(Blocking),HitFor(Separated)}})
    {
        const auto Mixed=Resolve(Hits);
        TestTrue(TEXT("A true wall vetoes the separated body in every iteration order"),Mixed.Decision==Decision::Blocked);
        TestEqual(TEXT("All raw blocking bodies are inspected without early success"),Mixed.UniqueBodies,2);
        TestEqual(TEXT("The genuine wall remains recorded independently"),Mixed.BlockedBodies,1);
    }
    auto* Ceiling=MakeBody({Center+FVector(-500,-500,90),Center+FVector(500,-500,90),Center+FVector(0,500,90)},FTransform::Identity);
    TestTrue(TEXT("A true ceiling vetoes an otherwise separated body"),Resolve({HitFor(Separated),HitFor(Ceiling)}).Decision==Decision::Blocked);
    TArray<FVector> MixedFaces=Authored;MixedFaces.Append(Wall);auto* MixedMesh=MakeBody(MixedFaces,FTransform::Identity);
    TestTrue(TEXT("A contacting face in the same selected cooked shape vetoes all-body separation"),Resolve({HitFor(MixedMesh)}).Decision==Decision::Blocked);
    FOverlapResult Missing;Missing.bBlockingHit=true;Missing.SetItemIndex(INDEX_NONE);
    TestTrue(TEXT("A missing body prevents all-contact separation"),Resolve({HitFor(Separated),Missing}).Decision==Decision::Unresolved);
    auto* ItemActor=World->SpawnActor<AActor>();auto* ItemMesh=NewObject<UInstancedStaticMeshComponent>(ItemActor);
    ItemActor->SetRootComponent(ItemMesh);ItemMesh->SetMobility(EComponentMobility::Static);ItemMesh->SetHiddenInGame(true);
    ItemMesh->bMultiBodyOverlap=true;
    ItemMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    ItemMesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);ItemMesh->RegisterComponent();
    ItemMesh->AddInstance(FTransform(Center),true);ItemMesh->AddInstance(FTransform(Center+FVector(1000,0,0)),true);
    TestTrue(TEXT("Same-component item control creates two real native per-instance bodies"),
        ItemMesh->GetBodyInstance(NAME_None,false,0) && ItemMesh->GetBodyInstance(NAME_None,false,1)
        && ItemMesh->GetBodyInstance(NAME_None,false,0)!=ItemMesh->GetBodyInstance(NAME_None,false,1));
    const auto Items=Resolve({HitFor(ItemMesh,0),HitFor(ItemMesh,1)});
    TestEqual(TEXT("Different body-item IDs on one component are not deduplicated"),Items.UniqueBodies,2);
    TestTrue(TEXT("Unsupported per-item bodies fail closed"),Items.Decision==Decision::Unresolved);
    const auto Repeated=Resolve({HitFor(Separated),HitFor(Separated)});
    TestEqual(TEXT("Repeated identical hits preserve raw hit accounting"),Repeated.RawBlockingHits,2);
    TestEqual(TEXT("Repeated identical hits inspect their body once"),Repeated.UniqueBodies,1);
    TestTrue(TEXT("Consistent duplicate hits retain their complete typed separation decision"),Repeated.Decision==Decision::Separated);
    auto Inconsistent=HitFor(Separated);Inconsistent.PhysicsObject=Blocking->GetPhysicsObjectByName(NAME_None);
    TestTrue(TEXT("Duplicate-body binding control uses a real different native physics object"),Inconsistent.PhysicsObject!=nullptr);
    const auto InconsistentResult=Resolve({HitFor(Separated),Inconsistent});
    TestTrue(TEXT("Inconsistent duplicate hit cannot reuse the first body's separation"),InconsistentResult.Decision==Decision::Unresolved);
    TestEqual(TEXT("Inconsistent duplicate veto retains unique-body accounting"),InconsistentResult.UniqueBodies,1);
    TestEqual(TEXT("Inconsistent duplicate replaces separated disposition with unresolved"),InconsistentResult.UnresolvedBodies,1);
    TestTrue(TEXT("Invalid capsule input cannot be mistaken for raw scene clearance"),
        WarCitadelCookedContacts::ResolveOverlaps({},Center,FQuat::Identity,0,96,false).Decision==Decision::Unresolved);
    auto* Unknown=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Unknown);Unknown->SetRootComponent(Box);
    Box->SetMobility(EComponentMobility::Static);Box->SetBoxExtent(FVector(5));Unknown->SetActorLocation(Center+FVector(1000,0,0));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Box->RegisterComponent();
    TestTrue(TEXT("An unsupported selected simple shape never uses a triangle certificate"),Resolve({HitFor(Separated),HitFor(Box)}).Decision==Decision::Unresolved);
    auto* WeldParent=MakeBody(Authored,FTransform::Identity);auto* WeldChild=MakeBody(Wall,FTransform::Identity);
    TestTrue(TEXT("Welded-child control actually creates a native weld"),WeldParent->GetBodyInstance(NAME_None,false)->Weld(WeldChild->GetBodyInstance(NAME_None,false),FTransform::Identity));
    TestTrue(TEXT("Original child identity retains the real native weld parent"),WeldChild->GetBodyInstance(NAME_None,false)->WeldParent!=nullptr);
    TestTrue(TEXT("A welded child cannot be disguised as its separated parent"),Resolve({HitFor(WeldChild)}).Decision==Decision::Unresolved);
    TestTrue(TEXT("A root with foreign selected-query child shapes cannot certify separation"),Resolve({HitFor(WeldParent)}).Decision!=Decision::Separated);
    WeldParent->GetBodyInstance(NAME_None,false)->UnWeld(WeldChild->GetBodyInstance(NAME_None,false));
    TestTrue(TEXT("Test weld is detached before temporary native physics teardown"),WeldChild->GetBodyInstance(NAME_None,false)->WeldParent==nullptr);
    // A contacting face exactly on a query-box boundary must survive the live
    // BVH's float conversion; scaled/mirrored bodies are intentionally unresolved.
    const TArray<FVector> Boundary={{42,-100,-100},{42,100,-100},{42,0,200}};
    for (const FVector& Scale:{FVector(1,1,1),FVector(.90416663885,1,1),FVector(-1,1,1)})
    {
        const FTransform Transform(FRotator(0,90,0),FVector(1000,2000,3000),Scale);
        auto* Mesh=MakeBody(Boundary,Transform);Witness=Inspect(Mesh,Transform.GetLocation());
        TestTrue(TEXT("Boundary witness enters the actual native physics read lock"),Witness->GetBoolField(TEXT("readLockEntered")));
        int32 Candidates=0;
        for (const auto& Shape:Witness->GetArrayField(TEXT("shapes")))
        {
            const auto Row=Shape->AsObject();double Count=0;
            if (Row->GetBoolField(TEXT("selected")) && Row->TryGetNumberField(TEXT("candidateTriangleCount"),Count)) Candidates+=int32(Count);
        }
        TestTrue(TEXT("Live rotated, scaled and mirrored BVH retains the contacting boundary face"),Candidates>=1);
        TestFalse(TEXT("Contacting or unsupported scaled/mirrored geometry never certifies separation"),Witness->GetBoolField(TEXT("separatedContactDiagnostic")));
    }
    World->EndPlay(EEndPlayReason::Quit);GEngine->DestroyWorldContext(World);World->DestroyWorld(false);return true;
}
#endif
