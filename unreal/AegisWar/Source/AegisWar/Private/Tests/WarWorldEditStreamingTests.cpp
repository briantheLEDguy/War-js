#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWorldEditSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Level.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWorldEditStreamingTest, "AegisWar.Foundation.WorldEditStreaming",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarWorldEditStreamingTest::RunTest(const FString& Parameters)
{
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Editor, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Streaming history test world"), World)) return false;
    auto* Edit = World->GetSubsystem<UWarWorldEditSubsystem>();
    auto* Actor = World->SpawnActor<AStaticMeshActor>();
    auto* Mesh = LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")); // Invisible test geometry only.
    if (!TestNotNull(TEXT("GM subsystem"),Edit) || !TestNotNull(TEXT("Fixture actor"),Actor)
        || !TestNotNull(TEXT("Fixture mesh"),Mesh)) { World->DestroyWorld(false); return false; }
    Actor->GetStaticMeshComponent()->SetStaticMesh(Mesh);
    Actor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("NoCollision"));
    Actor->SetActorHiddenInGame(true);
    const FString Hash = FString::ChrN(64, TEXT('a'));
    Actor->Tags = {TEXT("WarCapitalBuilding"), TEXT("WarWorldObject_fixture"), FName(*(TEXT("WarModelSha256_")+Hash))};
    const FName Id(TEXT("fixture"));
    FString Error;
    TestTrue(TEXT("Initialize authored document"), Edit->History.Initialize({{Id,Actor->GetActorTransform(),true,Mesh->GetPathName()+TEXT(":")+Hash}},Error));
    UWarWorldEditSubsystem::FModelTemplate Template;
    Template.Mesh=Mesh; Template.LevelPackage=World->PersistentLevel->GetOutermost()->GetFName();
    for (int32 Index=0;Index<Actor->GetStaticMeshComponent()->GetNumMaterials();++Index)
        Template.Materials.Add(Actor->GetStaticMeshComponent()->GetMaterial(Index));
    Edit->Templates.Add(Id,Template); Edit->BaselineLevels.Add(Id,Template.LevelPackage); Edit->Actors.Add(Id,Actor); Edit->bInitialized=true;
    TestTrue(TEXT("Draft can differ from its immutable source"), Edit->History.Edit(Id,FTransform(FVector(100,0,0)),true,Edit->History.GetRevision(),Error));
    const FString Before=Edit->History.ExportDraft();
    Edit->LevelRemoved(World->PersistentLevel,World);
    TestNull(TEXT("Unload drops actor reference"),Edit->GetObjectActor(Id));
    Edit->LevelAdded(World->PersistentLevel,World);
    TestTrue(TEXT("Reload restores the draft placement"),Actor->GetActorLocation().Equals(FVector(100,0,0)));
    TestEqual(TEXT("Reload preserves complete history"),Edit->History.ExportDraft(),Before);
    Edit->LevelRemoved(World->PersistentLevel,World);
    Actor->SetActorLocation(FVector(500,0,0));
    Edit->LevelAdded(World->PersistentLevel,World);
    TestFalse(TEXT("Changed authored placement produces a conflict"),Edit->StreamingConflict.IsEmpty());
    TestTrue(TEXT("Conflicting owner placement is not overwritten"),Actor->GetActorLocation().Equals(FVector(500,0,0)));
    TestEqual(TEXT("Conflicts retain document and undo history"),Edit->History.ExportDraft(),Before);
    World->DestroyWorld(false); return true;
}
#endif
