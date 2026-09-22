#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarGraphicsSettings.h"
#include "WarGraphicsBootstrap.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarGraphicsRulesTest, "AegisWar.Foundation.GraphicsRules",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarGraphicsRulesTest::RunTest(const FString&)
{
    FWarGraphicsSnapshot V;
    TestEqual(TEXT("Default preset"), WarGraphics::Preset(V), 0);
    TestEqual(TEXT("Default scale"), V.Quality.ResolutionQuality, 75.f);
    V.FrameLimit = 144; V.bVSync = false; V.Resolution = FIntPoint(2560, 1440);
    WarGraphics::SetPreset(V, 3);
    TestEqual(TEXT("Preset preserves frame cap"), V.FrameLimit, 144.f);
    TestFalse(TEXT("Preset preserves VSync"), V.bVSync);
    TestEqual(TEXT("Preset preserves scale"), V.Quality.ResolutionQuality, 75.f);
    TestEqual(TEXT("Preset preserves resolution"), V.Resolution, FIntPoint(2560, 1440));
    TestEqual(TEXT("Epic recognized independent of render scale"), WarGraphics::Preset(V), 3);
    V.Quality.ViewDistanceQuality = 1;
    TestEqual(TEXT("View override produces Custom"), WarGraphics::Preset(V), -1);
    V.FrameLimit = std::numeric_limits<float>::quiet_NaN();
    V.Quality.ResolutionQuality = std::numeric_limits<float>::infinity();
    V.Resolution = FIntPoint(-1, MAX_int32); V.Mode = static_cast<EWindowMode::Type>(99);
    V.Quality.ShadowQuality = -10;
    WarGraphics::Sanitize(V, 80, 100);
    TestEqual(TEXT("NaN cap repaired"), V.FrameLimit, 60.f);
    TestEqual(TEXT("Scale uses engine minimum"), V.Quality.ResolutionQuality, 80.f);
    TestEqual(TEXT("Corrupt resolution repaired"), V.Resolution, FIntPoint(1280, 720));
    TestEqual(TEXT("Corrupt mode repaired"), V.Mode, EWindowMode::Windowed);
    TestEqual(TEXT("Quality bounded"), V.Quality.ShadowQuality, 0);
    TArray<FIntPoint> Resolutions{{1920,1080},{1280,720},{0,0},{1280,720},{9000,9000},{-1,720}};
    WarGraphics::FilterResolutions(Resolutions, FIntPoint(1920,1080));
    TestEqual(TEXT("Invalid and duplicate modes removed"), Resolutions.Num(), 2);
    TestEqual(TEXT("Sorted resolution list"), Resolutions[0], FIntPoint(1280,720));
    TestEqual(TEXT("Mode change avoids a silent high-resolution jump"), WarGraphics::PickResolution(FIntPoint(1280,800),
        {FIntPoint(7680,4320), FIntPoint(1280,720), FIntPoint(1920,1080)}), FIntPoint(1280,720));
    TestEqual(TEXT("Supported current resolution retained"), WarGraphics::PickResolution(FIntPoint(1920,1080), Resolutions), FIntPoint(1920,1080));
    TestEqual(TEXT("Missing enumeration retains current resolution"), WarGraphics::PickResolution(FIntPoint(1024,768), {}), FIntPoint(1024,768));
    FWarGraphicsCapabilities C;
    C.bCanRender = true; C.bCanChangeDisplay = true; C.bFullscreen = true;
    C.Desktop = FIntPoint(1920,1080); C.WorkArea = FIntPoint(1888,1016);
    C.FullscreenResolutions = Resolutions; C.WindowedResolutions = {FIntPoint(1280,720)};
    FWarGraphicsSnapshot Applied; Applied.Mode = EWindowMode::Windowed;
    auto Draft = Applied; Draft.Mode = EWindowMode::Fullscreen; Draft.Resolution = C.Desktop;
    FString Error;
    TestTrue(TEXT("Enumerated fullscreen mode accepted"), WarGraphics::Validate(Draft, Applied, C, Error));
    C.bFullscreen = false;
    TestFalse(TEXT("Unsupported exclusive mode rejected"), WarGraphics::Validate(Draft, Applied, C, Error));
    C.FullscreenResolutions.Reset(); C.WindowedResolutions.Reset();
    TestTrue(TEXT("Enumeration failure preserves working mode"), WarGraphics::Validate(Applied, Applied, C, Error));
    Draft = Applied; Draft.Mode = EWindowMode::WindowedFullscreen; Draft.Resolution = C.Desktop;
    TestTrue(TEXT("Borderless uses desktop"), WarGraphics::Validate(Draft, Applied, C, Error));
    Draft.Resolution = FIntPoint(1280,720);
    TestFalse(TEXT("Borderless rejects arbitrary resolution"), WarGraphics::Validate(Draft, Applied, C, Error));
    C.bCanChangeDisplay = false;
    TestFalse(TEXT("Embedded viewport rejects switching"), WarGraphics::Validate(Draft, Applied, C, Error));
    C.bCanRender = false;
    TestFalse(TEXT("Headless rejects even quality changes"), WarGraphics::Validate(Applied, Applied, C, Error));
    C.WorkArea = FIntPoint(800,600); C.Desktop = FIntPoint(832,664);
    const auto Recovered = WarGraphics::Recovery(Draft, C);
    TestEqual(TEXT("Disconnected monitor falls back to window"), Recovered.Mode, EWindowMode::Windowed);
    TestEqual(TEXT("Recovery fits small monitor"), Recovered.Resolution, FIntPoint(800,600));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarGraphicsTransactionTest, "AegisWar.Foundation.GraphicsTransactions",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarGraphicsTransactionTest::RunTest(const FString&)
{
    const FString TestIni = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("GraphicsAutomation.ini"));
    TGuardValue<FString> ConfigGuard(GGameUserSettingsIni, TestIni);
    GConfig->Add(TestIni, FConfigFile());
    GConfig->SetString(TEXT("AegisWar.Controls"), TEXT("Forward"), TEXT("Up"), TestIni);
    auto* Settings = NewObject<UWarGraphicsSettings>();
    Settings->SetToDefaults(); Settings->SetScreenResolution(FIntPoint(1280,720));
    Settings->UpdateVersion(); Settings->BeginEditing();
    const auto Original = Settings->Capture();
    Settings->Draft.FrameLimit = 120;
    TestTrue(TEXT("Draft does not mutate engine object"), Settings->Capture() == Original);
    Settings->EndEditing();
    TestTrue(TEXT("Cancel restores draft"), Settings->Draft == Settings->GetApplied());
    Settings->Confirmed = Original; Settings->bPreviewing = true;
    Settings->SetScreenResolution(FIntPoint(1600,900));
    Settings->ConfirmVideoMode();
    TestEqual(TEXT("Engine resize auto-confirm cannot persist preview dimensions"), Settings->GetScreenResolution(), Original.Resolution);
    Settings->Draft.FrameLimit = 120; Settings->Deadline = FPlatformTime::Seconds() - 1;
    Settings->SaveSettings();
    TestFalse(TEXT("Preview cannot save to disk"), IFileManager::Get().FileExists(*TestIni));
    TestFalse(TEXT("Expired preview stops ticking"), Settings->TickPreview(0));
    TestFalse(TEXT("Expired preview cleared"), Settings->IsPreviewing());
    TestTrue(TEXT("Timeout restores draft"), Settings->Draft == Original);
    Settings->bPreviewing = true; Settings->Draft.FrameLimit = 120;
    Settings->OnActivation(false);
    TestFalse(TEXT("Focus loss rolls back"), Settings->IsPreviewing());
    Settings->bPreviewing = true;
    Settings->EndEditing();
    TestFalse(TEXT("Closing page rolls back"), Settings->IsPreviewing());
    TestFalse(TEXT("Cannot confirm without active preview"), Settings->Keep());
    Settings->bPreviewing = true; Settings->bDisplayVerified = false;
    TestFalse(TEXT("Cannot confirm unverified display"), Settings->Keep());
    Settings->EndEditing();
    FString Binding;
    TestTrue(TEXT("Unrelated preferences retained"), GConfig->GetString(TEXT("AegisWar.Controls"), TEXT("Forward"), Binding, TestIni));
    TestEqual(TEXT("Binding value unchanged"), Binding, FString(TEXT("Up")));
    // A regular file used as the parent guarantees a write failure without changing
    // permissions on player files or relying on host-specific readonly semantics.
    const FString Blocker = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("GraphicsWriteBlocker.tmp"));
    FFileHelper::SaveStringToFile(TEXT("graphics test"), *Blocker);
    {
        const FString BadIni = FPaths::Combine(Blocker, TEXT("Preferences.ini"));
        TGuardValue<FString> BadPathGuard(GGameUserSettingsIni, BadIni);
        GConfig->Add(BadIni, FConfigFile());
        Settings->SaveSettings();
        TestFalse(TEXT("Write failure is not reported as saved"), Settings->bLastSaveSucceeded);
        GConfig->UnloadFile(BadIni);
    }
    IFileManager::Get().Delete(*Blocker);
    GConfig->UnloadFile(TestIni);
    IFileManager::Get().Delete(*TestIni);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarGraphicsBootstrapTest, "AegisWar.Foundation.GraphicsStartup",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarGraphicsBootstrapTest::RunTest(const FString&)
{
    FConfigCacheIni Config(EConfigCacheType::Temporary);
    const FString Ini = TEXT("GraphicsStartupTest.ini");
    const TCHAR* Section = TEXT("/Script/AegisWar.WarGraphicsSettings");
    Config.Add(Ini, FConfigFile());
    Config.SetInt(TEXT("/Script/Engine.GameUserSettings"), TEXT("FullscreenMode"), 2, Ini);
    Config.SetInt(TEXT("/Script/Engine.GameUserSettings"), TEXT("ResolutionSizeX"), 1600, Ini);
    Config.SetInt(TEXT("/Script/Engine.GameUserSettings"), TEXT("ResolutionSizeY"), 900, Ini);
    Config.SetFloat(TEXT("/Script/Engine.GameUserSettings"), TEXT("FrameRateLimit"), 90, Ini);
    Config.SetString(TEXT("AegisWar.Controls"), TEXT("Forward"), TEXT("Up"), Ini);
    WarGraphicsBootstrap::PrepareConfig(Config, Ini, false);
    int32 Width = 0, Mode = -1; float Cap = 0;
    Config.GetInt(Section, TEXT("ResolutionSizeX"), Width, Ini);
    Config.GetFloat(Section, TEXT("FrameRateLimit"), Cap, Ini);
    TestEqual(TEXT("Legacy resolution migrated"), Width, 1600);
    TestEqual(TEXT("Legacy cap migrated"), Cap, 90.f);
    Config.SetFloat(Section, TEXT("FrameRateLimit"), 120, Ini);
    WarGraphicsBootstrap::PrepareConfig(Config, Ini, false);
    Config.GetFloat(Section, TEXT("FrameRateLimit"), Cap, Ini);
    TestEqual(TEXT("Migration never overwrites new preferences"), Cap, 120.f);
    Config.SetInt(Section, TEXT("FullscreenMode"), 99, Ini);
    WarGraphicsBootstrap::PrepareConfig(Config, Ini, false);
    Config.GetInt(Section, TEXT("FullscreenMode"), Mode, Ini);
    TestEqual(TEXT("Corrupt mode repaired before window creation"), Mode, 2);
    WarGraphicsBootstrap::PrepareConfig(Config, Ini, true);
    Config.GetInt(Section, TEXT("ResolutionSizeX"), Width, Ini);
    Config.GetFloat(Section, TEXT("FrameRateLimit"), Cap, Ini);
    TestEqual(TEXT("Safe startup resolution"), Width, 1280);
    TestEqual(TEXT("Safe startup cap"), Cap, 60.f);
    FString Key;
    Config.GetString(TEXT("AegisWar.Controls"), TEXT("Forward"), Key, Ini);
    TestEqual(TEXT("Migration and recovery preserve controls"), Key, FString(TEXT("Up")));
    const FString NewIni = TEXT("GraphicsFirstRunTest.ini");
    Config.Add(NewIni, FConfigFile());
    WarGraphicsBootstrap::PrepareConfig(Config, NewIni, false);
    Config.GetInt(Section, TEXT("FullscreenMode"), Mode, NewIni);
    TestEqual(TEXT("First launch is borderless"), Mode, 1);
    return true;
}
#endif
