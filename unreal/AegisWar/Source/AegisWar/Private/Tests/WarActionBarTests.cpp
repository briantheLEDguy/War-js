#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarPlayerController.h"
#include "WarControlSettings.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarActionBarTest, "AegisWar.Foundation.ActionBars",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarActionBarTest::RunTest(const FString& Parameters)
{
    // All persistence exercises use a disposable config, never the player's preferences.
    const FString TestIni = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("ActionBarsAutomation.ini"));
    TGuardValue<FString> ConfigGuard(GGameUserSettingsIni, TestIni);
    GConfig->Add(TestIni, FConfigFile());
    GConfig->EmptySection(TEXT("AegisWar.Controls"), TestIni);
    GConfig->EmptySection(TEXT("AegisWar.ActionBar"), TestIni);
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Test world"), World)) return false;
    auto& Context = GEngine->CreateNewWorldContext(EWorldType::Game); Context.SetCurrentWorld(World);
    auto* PC = World->SpawnActor<AWarPlayerController>();
    PC->LoadControlKeys();
    TestEqual(TEXT("Default bar has ten slots"), PC->GetActionBars()[0].Buttons, 10);
    TestEqual(TEXT("First slot binding"), PC->GetControlKey(WarActionBar::Binding(0)), EKeys::One);
    TestEqual(TEXT("Tenth slot binding"), PC->GetControlKey(WarActionBar::Binding(9)), EKeys::Zero);
    TestEqual(TEXT("Invalid zero-button bar rejected"), PC->AddActionBar(0), INDEX_NONE);
    TestEqual(TEXT("Invalid eleven-button bar rejected"), PC->AddActionBar(11), INDEX_NONE);
    const int32 Id = PC->AddActionBar(3), Slot = Id * 10 + 2;
    TestTrue(TEXT("Custom slot assigns a native action"), PC->SetActionSlot(Slot, TEXT("health_potion")));
    TestFalse(TEXT("Unimplemented class ability cannot masquerade as strike"), PC->SetActionSlot(Slot, TEXT("ember_arcanist.spark_lash")));
    FString Error;
    TestFalse(TEXT("Duplicate movement key rejected"), PC->SetControlKey(WarActionBar::Binding(Slot), EKeys::W, Error));
    TestTrue(TEXT("Custom button binding saved"), PC->SetControlKey(WarActionBar::Binding(Slot), EKeys::P, Error));
    TestFalse(TEXT("Absent button cannot bind"), PC->SetControlKey(WarActionBar::Binding(Slot + 1), EKeys::O, Error));
    PC->MoveActionBar(Id, FVector2D(-2, 4), true);
    PC->ResizeActionBar(Id, 1);
    TestFalse(TEXT("Shrunken slot cannot activate"), PC->HasActionSlot(Slot));
    PC->ActivateActionSlot(Slot);
    FConfigFile DiskConfig;
    TestTrue(TEXT("Layout writes to disk"), IFileManager::Get().FileExists(*TestIni));
    DiskConfig.Read(TestIni);
    FString SavedIds;
    TestTrue(TEXT("Disk contains bar identities"), DiskConfig.GetString(TEXT("AegisWar.ActionBar"), TEXT("Bars"), SavedIds));
    TestEqual(TEXT("Disk preserves both bars"), SavedIds, FString(TEXT("0,1")));
    auto* Reloaded = World->SpawnActor<AWarPlayerController>(); Reloaded->LoadControlKeys();
    TestEqual(TEXT("Saved bar count reloads"), Reloaded->GetActionBars().Num(), 2);
    if (Reloaded->GetActionBars().Num() == 2)
    {
        TestEqual(TEXT("Custom size reloads"), Reloaded->GetActionBars()[1].Buttons, 1);
        TestEqual(TEXT("Position clamps and reloads"), Reloaded->GetActionBars()[1].Position, FVector2D(0, 1));
    }
    Reloaded->ResizeActionBar(Id, 3);
    TestEqual(TEXT("Resizing preserves hidden assignment across reload"), Reloaded->GetActionSlot(Slot), FName(TEXT("health_potion")));
    TestEqual(TEXT("Resizing preserves hidden key across reload"), Reloaded->GetControlKey(WarActionBar::Binding(Slot)), EKeys::P);
    TestFalse(TEXT("No pawn means no executable action"), Reloaded->GetActionSlotView(Slot).bAvailable);
    Reloaded->RemoveActionBar(Id);
    TestFalse(TEXT("Removed slots cannot activate"), Reloaded->HasActionSlot(Slot));
    TestFalse(TEXT("Removed bar releases key"), Reloaded->GetControlKey(WarActionBar::Binding(Slot)).IsValid());
    for (int32 Index = 0; Index < 32; ++Index) TestTrue(TEXT("No fixed bar-count limit"), Reloaded->AddActionBar(Index % 10 + 1) != INDEX_NONE);
    TestEqual(TEXT("All created bars retained"), Reloaded->GetActionBars().Num(), 33);
    TestFalse(TEXT("Malformed slot action rejected"), WarControls::Validate(TEXT("ActionSlotgarbage"), EKeys::O, {}, Error));
    TestFalse(TEXT("Decimal slot identifiers rejected"), WarControls::Validate(TEXT("ActionSlot1.5"), EKeys::O, {}, Error));
    // A pre-existing binding wins over a newly introduced default.
    GConfig->SetString(TEXT("AegisWar.Controls"), TEXT("Forward"), TEXT("One"), TestIni);
    GConfig->RemoveKey(TEXT("AegisWar.Controls"), TEXT("ActionSlot1"), TestIni);
    auto* Migrated = World->SpawnActor<AWarPlayerController>(); Migrated->LoadControlKeys();
    TestEqual(TEXT("Existing movement binding preserved"), Migrated->GetControlKey(TEXT("Forward")), EKeys::One);
    TestFalse(TEXT("Conflicting new default remains unbound"), Migrated->GetControlKey(TEXT("ActionSlot1")).IsValid());
    GEngine->DestroyWorldContext(World); World->DestroyWorld(false);
    GConfig->UnloadFile(TestIni); IFileManager::Get().Delete(*TestIni);
    return true;
}
#endif
