#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarCraftingStation.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "WarCharacter.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarStationTest, "AegisWar.Foundation.CraftingStationInteraction",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarStationTest::RunTest(const FString& Parameters)
{
    FString Json;
    if (!TestTrue(TEXT("Authored table import receipt exists"), FFileHelper::LoadFileToString(Json,
        *FPaths::Combine(FPaths::ProjectDir(), TEXT("../../artifacts/unreal/converted/frontier_field_command_table/editor-import.json"))))) return false;
    TSharedPtr<FJsonObject> Root;
    if (!TestTrue(TEXT("Import receipt parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))) return false;
    const FString Path = Root->GetArrayField(TEXT("meshes"))[0]->AsObject()->GetStringField(TEXT("path"));
    UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
    if (!TestNotNull(TEXT("Imported authored table mesh"), Mesh)) return false;
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Station test world"), World)) return false;
    auto* Station = World->SpawnActor<AWarCraftingStation>();
    auto* Pawn = World->SpawnActor<AWarCharacter>();
    if (!Station || !Pawn) { World->DestroyWorld(false); return false; }
    TestFalse(TEXT("Missing model cannot be used"), Station->CanInteract(Pawn));
    Station->GetStaticMeshComponent()->SetStaticMesh(Mesh);
    Pawn->SetActorLocation(Station->GetActorLocation() + FVector(500, 0, 0));
    TestTrue(TEXT("Boundary range accepted"), Station->CanInteract(Pawn));
    Pawn->SetActorLocation(Station->GetActorLocation() + FVector(501, 0, 0));
    TestFalse(TEXT("Outside range rejected"), Station->CanInteract(Pawn));
    Pawn->SetActorLocation(Station->GetActorLocation());
    Station->SetActorHiddenInGame(true);
    TestFalse(TEXT("Hidden station rejected"), Station->CanInteract(Pawn));
    Station->SetActorHiddenInGame(false);
    Station->GetStaticMeshComponent()->SetVisibility(false);
    TestFalse(TEXT("Invisible component rejected"), Station->CanInteract(Pawn));
    Station->GetStaticMeshComponent()->SetVisibility(true);
    Station->InteractionRadius = 0;
    TestFalse(TEXT("Invalid radius rejected"), Station->CanInteract(Pawn));
    Station->InteractionRadius = 500;
    TestFalse(TEXT("Missing pawn rejected"), Station->CanInteract(nullptr));
    UWorld* Other = UWorld::CreateWorld(EWorldType::Game, false);
    auto* RemotePawn = Other->SpawnActor<AWarCharacter>();
    TestFalse(TEXT("Other-world pawn rejected"), Station->CanInteract(RemotePawn));
    Other->DestroyWorld(false);
    World->DestroyWorld(false);
    return true;
}
#endif
