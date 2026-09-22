#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarGmRules.h"
#include "WarRuntimeSettings.h"
#include "WarWorldEditSubsystem.h"
#include "WarPlayerController.h"
#include "GameFramework/Pawn.h"
#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarLocalGmAccessTest, "AegisWar.Foundation.LocalGmAccess",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarLocalGmAccessTest::RunTest(const FString& Parameters)
{
    using WarGmRules::AllowsDevelopmentSession;
    TestTrue(TEXT("Project launch enables standalone GM without a command line flag"),
        AllowsDevelopmentSession(false, NM_Standalone, EWorldType::Game, true, false));
    TestFalse(TEXT("Disabling the setting restores standalone opt-in"),
        AllowsDevelopmentSession(false, NM_Standalone, EWorldType::Game, false, false));
    TestTrue(TEXT("Explicit development launch still works"),
        AllowsDevelopmentSession(false, NM_Standalone, EWorldType::Game, false, true));
    TestTrue(TEXT("Local editor Play retains access"),
        AllowsDevelopmentSession(false, NM_Standalone, EWorldType::PIE, false, false));
    for (const auto Type : {EWorldType::Game, EWorldType::PIE})
    {
        TestFalse(TEXT("Shipping cannot enable GM"), AllowsDevelopmentSession(true, NM_Standalone, Type, true, true));
        for (const auto Mode : {NM_Client, NM_ListenServer, NM_DedicatedServer})
            TestFalse(TEXT("No network role can enable local GM"), AllowsDevelopmentSession(false, Mode, Type, true, true));
    }
    for (const auto Type : {EWorldType::Editor, EWorldType::EditorPreview, EWorldType::GamePreview, EWorldType::None})
        TestFalse(TEXT("Non-play worlds cannot enable GM"), AllowsDevelopmentSession(false, NM_Standalone, Type, true, true));

    auto* Settings = GetMutableDefault<UWarRuntimeSettings>();
    TestTrue(TEXT("Repository project enables local GM by default"), Settings->bEnableLocalDevelopmentGM);
    const bool bPrevious = Settings->bEnableLocalDevelopmentGM;
    Settings->bEnableLocalDevelopmentGM = true;
    ON_SCOPE_EXIT { Settings->bEnableLocalDevelopmentGM = bPrevious; };
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("AegisCapital_Workbench"),
        CreatePackage(TEXT("/Game/Capitals/aegis_capital/AegisCapital_Workbench")), true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Standalone workbench world"), World)) return false;
    ON_SCOPE_EXIT { World->DestroyWorld(false); };
    auto* Editor = World->GetSubsystem<UWarWorldEditSubsystem>();
    auto* Player = World->SpawnActor<AWarPlayerController>();
    if (!TestNotNull(TEXT("Workbench subsystem"), Editor) || !TestNotNull(TEXT("Local controller"), Player)) return false;
    TestFalse(TEXT("Missing controller remains denied"), Editor->CanUse(nullptr));
    TestFalse(TEXT("Character selection cannot use GM before entry"), Editor->CanUse(Player));
    auto* Pawn = World->SpawnActor<APawn>();
    if (!TestNotNull(TEXT("Test pawn"), Pawn)) return false;
    Player->Possess(Pawn);
    TestFalse(TEXT("A controller without a local player remains denied"), Editor->CanUse(Player));
    Player->Player = NewObject<ULocalPlayer>(GEngine);
    TestEqual(TEXT("Fixture uses the supported workbench package"), World->GetOutermost()->GetName(),
        FString(TEXT("/Game/Capitals/aegis_capital/AegisCapital_Workbench")));
    TestTrue(TEXT("Fixture controller has authority"), Player->HasAuthority());
    TestTrue(TEXT("Fixture controller is local"), Player->IsLocalController());
    TestTrue(TEXT("Fixture controller possesses the pawn"), Player->GetPawn() == Pawn);
    TestTrue(TEXT("Fixture entry has no failure"), Player->GetEntryFailure().IsEmpty());
    TestTrue(TEXT("Real local workbench access uses the configured default"), Editor->CanUse(Player));
    Player->UnPossess();
    TestFalse(TEXT("Leaving the character revokes access"), Editor->CanUse(Player));
    return true;
}
#endif
