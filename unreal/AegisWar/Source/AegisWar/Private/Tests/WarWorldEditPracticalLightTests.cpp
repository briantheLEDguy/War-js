#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWorldEditSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/PointLight.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWorldEditPracticalLightTest, "AegisWar.Foundation.WorldEditPracticalLights",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarWorldEditPracticalLightTest::RunTest(const FString& Parameters)
{
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Editor, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Practical fixture test world"), World)) return false;
    auto* Edit = World->GetSubsystem<UWarWorldEditSubsystem>();
    auto* Parent = World->SpawnActor<AStaticMeshActor>();
    auto* Mesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")); // Invisible test geometry only.
    auto* Fixture = World->SpawnActor<APointLight>();
    auto* Unrelated = World->SpawnActor<APointLight>();
    if (!Edit || !Parent || !Mesh || !Fixture || !Unrelated) { World->DestroyWorld(false); return false; }
    Parent->SetActorHiddenInGame(true); Parent->GetStaticMeshComponent()->SetStaticMesh(Mesh);
    auto* Light = Cast<UPointLightComponent>(Fixture->GetLightComponent());
    Fixture->Tags.Add(TEXT("WarCitadelDecorPractical"));
    Light->SetMobility(EComponentMobility::Movable); Light->SetIntensityUnits(ELightUnits::Lumens);
    Light->SetIntensity(7200); Light->SetTemperature(2700); Light->SetUseTemperature(true);
    Light->SetAttenuationRadius(2200); Light->SetSourceRadius(8); Light->SetCastShadows(true);
    const FTransform Offset(FRotator(0, 25, 0), FVector(70, 0, 450));
    Fixture->AttachToActor(Parent, FAttachmentTransformRules::KeepRelativeTransform);
    Light->SetRelativeTransform(Offset);
    // A separately attached unmarked light is never hidden, copied or destroyed.
    Unrelated->AttachToActor(Parent, FAttachmentTransformRules::KeepRelativeTransform);
    const FName Id(TEXT("lit_fixture")); FString Error;
    UWarWorldEditSubsystem::FModelTemplate Template;
    Template.Mesh = Mesh; Template.LevelPackage = World->PersistentLevel->GetOutermost()->GetFName();
    TestTrue(TEXT("Trusted attached fixture captured"), WarWorldEditPracticalLights::Capture(Parent, Template.PracticalLights, Error));
    TestEqual(TEXT("Unmarked light excluded"), Template.PracticalLights.Num(), 1);
    TestTrue(TEXT("Exact authored assembly matches"), WarWorldEditPracticalLights::Matches(Parent, Template.PracticalLights));
    Light->SetIntensity(7201);
    TestFalse(TEXT("Streaming rejects changed intensity"), WarWorldEditPracticalLights::Matches(Parent, Template.PracticalLights));
    Light->SetIntensity(7200); Light->SetRelativeLocation(FVector(71, 0, 450));
    TestFalse(TEXT("Streaming rejects changed emitter offset"), WarWorldEditPracticalLights::Matches(Parent, Template.PracticalLights));
    Light->SetRelativeTransform(Offset);
    Edit->History.Initialize({{Id, Parent->GetActorTransform(), true, TEXT("trusted-fixture")}}, Error);
    Edit->Templates.Add(Id, Template); Edit->BaselineLevels.Add(Id, Template.LevelPackage); Edit->Actors.Add(Id, Parent);
    auto Next = Edit->History;
    const FName Created(TEXT("gm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"));
    const FTransform Moved(FRotator(0, 90, 0), FVector(400, 200, 0), FVector(1.2, 1.2, 1.2));
    TestTrue(TEXT("Duplicate enters ordinary history"), Next.Create(Created, Id, Moved, Next.GetRevision(), Error));
    TestTrue(TEXT("History creates owned practical components"), Edit->ApplyHistory(Next, Error));
    AActor* Clone = Edit->GetObjectActor(Created);
    if (Clone) Clone->SetActorHiddenInGame(true);
    TArray<UPointLightComponent*> Lights;
    if (Clone) Clone->GetComponents(Lights);
    if (!TestEqual(TEXT("One practical on duplicated furnishing"), Lights.Num(), 1))
    { AddError(Error); World->DestroyWorld(false); return false; }
    auto* Copied = Lights[0];
    TestTrue(TEXT("Created light matches every captured renderer property"),
        WarWorldEditPracticalLights::MatchesCreated(Clone, Template.PracticalLights));
    Copied->SetIntensity(1);
    TestFalse(TEXT("Created light mismatch is observable"), WarWorldEditPracticalLights::MatchesCreated(Clone, Template.PracticalLights));
    Copied->SetIntensity(7200);
    TestEqual(TEXT("Lumens preserved"), Copied->Intensity, Light->Intensity);
    TestTrue(TEXT("Units and shadows preserved"), Copied->IntensityUnits == ELightUnits::Lumens && Copied->CastShadows);
    TestTrue(TEXT("Temperature and radius preserved"), Copied->bUseTemperature && Copied->Temperature == 2700
        && Copied->AttenuationRadius == 2200 && Copied->SourceRadius == 8);
    TestTrue(TEXT("Light follows rotated and scaled furnishing"), Copied->GetComponentTransform().Equals(Offset * Moved, .0001));
    const FString Draft = Edit->History.ExportDraft();
    auto Undo = Edit->History;
    TestTrue(TEXT("Undo removes created furnishing"), Undo.Undo(false, Undo.GetRevision(), Error) && Edit->ApplyHistory(Undo, Error));
    TestNull(TEXT("Undo releases clone"), Edit->GetObjectActor(Created));
    TestTrue(TEXT("Undo destroys its owned light"), !IsValid(Copied) || !Copied->IsRegistered());
    auto Reload = Edit->History;
    TestTrue(TEXT("Draft reload recreates fixture"), Reload.ImportDraft(Draft, Reload.GetRevision(), Error) && Edit->ApplyHistory(Reload, Error));
    Clone = Edit->GetObjectActor(Created); Lights.Reset(); if (Clone) Clone->GetComponents(Lights);
    if (Clone) Clone->SetActorHiddenInGame(true);
    TestEqual(TEXT("Reload has one light, without orphan duplication"), Lights.Num(), 1);
    TestTrue(TEXT("Reload restores complete light state"), WarWorldEditPracticalLights::MatchesCreated(Clone, Template.PracticalLights));
    auto Show = Edit->History;
    TestTrue(TEXT("Original show enters history"), Show.Edit(Id, Parent->GetActorTransform(), false, Show.GetRevision(), Error));
    TestTrue(TEXT("Showing parent restores its practical"), Edit->ApplyHistory(Show, Error) && !Fixture->IsHidden());
    auto Hide = Edit->History;
    TestTrue(TEXT("Original hide enters history"), Hide.Edit(Id, Parent->GetActorTransform(), true, Hide.GetRevision(), Error));
    TestTrue(TEXT("Hidden light inherits original visibility state"), Edit->ApplyHistory(Hide, Error) && Fixture->IsHidden());
    TestFalse(TEXT("Unmarked attached light remains unchanged"), Unrelated->IsHidden());
    Light->LightFunctionMaterial = NewObject<UMaterial>();
    TArray<FWarWorldEditPracticalLight> Rejected;
    TestFalse(TEXT("Unsupported light assets cannot be silently omitted"), WarWorldEditPracticalLights::Capture(Parent, Rejected, Error));
    Light->LightFunctionMaterial = nullptr; Light->Intensity = std::numeric_limits<float>::quiet_NaN();
    TestFalse(TEXT("Nonfinite authored light rejected"), WarWorldEditPracticalLights::Capture(Parent, Rejected, Error));
    Light->Intensity = 7200;
    WarWorldEditPracticalLights::DestroyAttached(Parent);
    TestTrue(TEXT("Owned original practical destroyed"), !IsValid(Fixture) || Fixture->IsActorBeingDestroyed());
    TestTrue(TEXT("Unmarked attached light survives"), IsValid(Unrelated) && !Unrelated->IsActorBeingDestroyed());
    World->DestroyWorld(false); return true;
}
#endif
