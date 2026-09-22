#include "WarGraphicsSettings.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "UnrealClient.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "GenericPlatform/GenericApplication.h"
#include "Kismet/KismetSystemLibrary.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "HAL/PlatformFile.h"

UWarGraphicsSettings* UWarGraphicsSettings::Get()
{
    return GEngine ? Cast<UWarGraphicsSettings>(GEngine->GetGameUserSettings()) : nullptr;
}

FWarGraphicsSnapshot UWarGraphicsSettings::Capture() const
{
    FWarGraphicsSnapshot V;
    V.Mode = GetFullscreenMode(); V.Resolution = GetScreenResolution(); V.Quality = ScalabilityQuality;
    V.FrameLimit = GetFrameRateLimit(); V.bVSync = IsVSyncEnabled();
    return V;
}

FWarGraphicsSnapshot UWarGraphicsSettings::Actual() const
{
    auto V = Capture();
    if (GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport)
    {
        V.Resolution = GEngine->GameViewport->Viewport->GetSizeXY();
        V.Mode = GEngine->GameViewport->Viewport->GetWindowMode();
    }
    return V;
}

void UWarGraphicsSettings::Write(const FWarGraphicsSnapshot& V)
{
    SetFullscreenMode(V.Mode); SetScreenResolution(V.Resolution);
    ScalabilityQuality = V.Quality; SetFrameRateLimit(V.FrameLimit); SetVSyncEnabled(V.bVSync);
}

void UWarGraphicsSettings::SetToDefaults()
{
    Super::SetToDefaults();
    SetFrameRateLimit(60); SetVSyncEnabled(true);
    ScalabilityQuality.SetFromSingleQualityLevel(0); ScalabilityQuality.ResolutionQuality = 75;
}

void UWarGraphicsSettings::LoadSettings(bool Force)
{
    Super::LoadSettings(Force);
    if (FParse::Param(FCommandLine::Get(), TEXT("WarSafeGraphics")))
    {
        SetToDefaults(); SetFullscreenMode(EWindowMode::Windowed);
        SetScreenResolution(FIntPoint(1280, 720));
    }
    // Do not call Super::ValidateSettings with an obsolete version: it deletes the whole
    // shared ini, including camera and bindings. Repair our fields without that data loss.
    UpdateVersion();
    auto V = Capture(); WarGraphics::Sanitize(V); Write(V);
}

void UWarGraphicsSettings::ValidateSettings()
{
    UpdateVersion();
    auto V = Capture(); WarGraphics::Sanitize(V); Write(V);
    Super::ValidateSettings();
}

void UWarGraphicsSettings::ConfirmVideoMode()
{
    // UGameEngine auto-confirms OS window resizes. During our preview that callback
    // must not overwrite the recovery baseline or expose preview fields to SaveConfig.
    if (bPreviewing) { Write(Confirmed); return; }
    Super::ConfirmVideoMode();
}

void UWarGraphicsSettings::SaveSettings()
{
    if (bPreviewing) return;
    // Keep game quality preferences out of the editor's global scalability ini.
    Scalability::SaveState(GGameUserSettingsIni);
    SaveConfig(CPF_Config, *GGameUserSettingsIni);
    if (auto* File = GConfig->FindConfigFile(GGameUserSettingsIni))
    {
        File->Dirty = true;
        if (!File->Write(GGameUserSettingsIni, false)) { bLastSaveSucceeded = false; return; }
    }
    // SaveConfig returns void, so verify the file rather than promising a successful write.
    FConfigFile Disk;
    FString WrittenText;
    if (FFileHelper::LoadFileToString(WrittenText, &IPlatformFile::GetPlatformPhysical(), *GGameUserSettingsIni))
        Disk.CombineFromBuffer(WrittenText, GGameUserSettingsIni);
    const FString Section = GetClass()->GetPathName();
    int32 X = 0, Y = 0, Mode = -1;
    float Cap = -1, Scale = -1;
    bool Sync = !IsVSyncEnabled();
    bLastSaveSucceeded = Disk.GetInt(*Section, TEXT("ResolutionSizeX"), X)
        && Disk.GetInt(*Section, TEXT("ResolutionSizeY"), Y)
        && Disk.GetInt(*Section, TEXT("FullscreenMode"), Mode)
        && Disk.GetFloat(*Section, TEXT("FrameRateLimit"), Cap)
        && Disk.GetBool(*Section, TEXT("bUseVSync"), Sync)
        && Disk.GetFloat(TEXT("ScalabilityGroups"), TEXT("sg.ResolutionQuality"), Scale)
        && FIntPoint(X, Y) == GetScreenResolution() && Mode == static_cast<int32>(GetFullscreenMode())
        && FMath::IsNearlyEqual(Cap, GetFrameRateLimit()) && Sync == IsVSyncEnabled()
        && FMath::IsNearlyEqual(Scale, ScalabilityQuality.ResolutionQuality);
    const TPair<const TCHAR*, int32> Groups[] = {
        {TEXT("ViewDistance"), ScalabilityQuality.ViewDistanceQuality}, {TEXT("AntiAliasing"), ScalabilityQuality.AntiAliasingQuality},
        {TEXT("Shadow"), ScalabilityQuality.ShadowQuality}, {TEXT("GlobalIllumination"), ScalabilityQuality.GlobalIlluminationQuality},
        {TEXT("Reflection"), ScalabilityQuality.ReflectionQuality}, {TEXT("PostProcess"), ScalabilityQuality.PostProcessQuality},
        {TEXT("Texture"), ScalabilityQuality.TextureQuality}, {TEXT("Effects"), ScalabilityQuality.EffectsQuality},
        {TEXT("Foliage"), ScalabilityQuality.FoliageQuality}, {TEXT("Shading"), ScalabilityQuality.ShadingQuality},
        {TEXT("Landscape"), ScalabilityQuality.LandscapeQuality}};
    for (const auto& Group : Groups)
    {
        int32 Level = -1;
        bLastSaveSucceeded &= Disk.GetInt(TEXT("ScalabilityGroups"), *(FString(TEXT("sg.")) + Group.Key + TEXT("Quality")), Level)
            && Level == Group.Value;
    }
    if (!bLastSaveSucceeded)
        UE_LOG(LogTemp, Warning, TEXT("Graphics persistence verification failed (%s): disk %dx%d mode=%d cap=%.1f scale=%.1f sync=%d; expected %dx%d mode=%d cap=%.1f scale=%.1f sync=%d"),
            *GGameUserSettingsIni, X, Y, Mode, Cap, Scale, Sync, GetScreenResolution().X, GetScreenResolution().Y, static_cast<int32>(GetFullscreenMode()),
            GetFrameRateLimit(), ScalabilityQuality.ResolutionQuality, IsVSyncEnabled());
}

FWarGraphicsCapabilities UWarGraphicsSettings::Capabilities() const
{
    FWarGraphicsCapabilities C;
    C.bCanRender = FApp::CanEverRender() && !IsRunningDedicatedServer() && FSlateApplication::IsInitialized()
        && GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport;
    if (!C.bCanRender) { C.Notice = TEXT("Graphics settings require a rendered game window."); return C; }
    float Normalized, Current;
    GetResolutionScaleInformationEx(Normalized, Current, C.MinScale, C.MaxScale);
    C.MinScale = FMath::IsFinite(C.MinScale) ? FMath::Clamp(C.MinScale, 50.f, 100.f) : 50.f;
    C.MaxScale = FMath::IsFinite(C.MaxScale) ? FMath::Clamp(C.MaxScale, C.MinScale, 100.f) : 100.f;
    FDisplayMetrics Metrics;
    FDisplayMetrics::RebuildDisplayMetrics(Metrics);
    FPlatformRect Display = {0, 0, Metrics.PrimaryDisplayWidth, Metrics.PrimaryDisplayHeight};
    FPlatformRect Work = Metrics.PrimaryDisplayWorkAreaRect;
    if (auto Window = GEngine->GameViewport->GetWindow())
    {
        const auto Center = Window->GetPositionInScreen() + Window->GetSizeInScreen() * 0.5;
        for (const auto& Monitor : Metrics.MonitorInfo)
        {
            const auto& R = Monitor.DisplayRect;
            if (Center.X >= R.Left && Center.X < R.Right && Center.Y >= R.Top && Center.Y < R.Bottom)
            { Display = R; Work = Monitor.WorkArea; break; }
        }
    }
    C.Desktop = FIntPoint(Display.Right - Display.Left, Display.Bottom - Display.Top);
    // Reserve room for decorations; the UI scales down for smaller displays.
    C.WorkArea = FIntPoint(FMath::Max(0, Work.Right - Work.Left - 32), FMath::Max(0, Work.Bottom - Work.Top - 64));
    UKismetSystemLibrary::GetConvenientWindowedResolutions(C.WindowedResolutions);
    if (C.WorkArea.X > 0 && C.WorkArea.Y > 0)
        C.WindowedResolutions.Add(FIntPoint(FMath::Min(1280, C.WorkArea.X), FMath::Min(720, C.WorkArea.Y)));
    const auto Live = Actual();
    if (Live.Mode == EWindowMode::Windowed) C.WindowedResolutions.Add(Live.Resolution);
    WarGraphics::FilterResolutions(C.WindowedResolutions, C.WorkArea);
    const bool Enumerated = UKismetSystemLibrary::GetSupportedFullscreenResolutions(C.FullscreenResolutions);
    WarGraphics::FilterResolutions(C.FullscreenResolutions, FIntPoint(32768, 32768));
    // macOS exposes desktop fullscreen rather than Windows-style exclusive switching.
    C.bFullscreen = Enumerated && C.FullscreenResolutions.Num() > 0 && !PLATFORM_MAC;
    const auto* World = GEngine->GameViewport->GetWorld();
    C.bCanChangeDisplay = C.Desktop.X > 0 && C.Desktop.Y > 0 && FPlatformProperties::SupportsWindowedMode()
        && !FPlatformProperties::HasFixedResolution() && (!World || World->WorldType != EWorldType::PIE)
        && !FParse::Param(FCommandLine::Get(), TEXT("RenderOffscreen"));
    if (!C.bCanChangeDisplay) C.Notice = TEXT("Display changes are unavailable in this viewport. Use Standalone Game or the game executable.");
    else if (!Enumerated) C.Notice = TEXT("Fullscreen modes could not be detected. The current mode is retained; windowed and borderless remain available.");
    if (FParse::Param(FCommandLine::Get(), TEXT("windowed")) || FParse::Param(FCommandLine::Get(), TEXT("fullscreen"))
        || FCString::Strifind(FCommandLine::Get(), TEXT("ResX=")) || FCString::Strifind(FCommandLine::Get(), TEXT("ResY=")))
        C.Notice += TEXT(" Launch display overrides apply again on the next launch.");
    const TPair<const TCHAR*, const TCHAR*> Overrides[] = {
        {TEXT("r.VSync"), TEXT("VSync")}, {TEXT("t.MaxFPS"), TEXT("Frame cap")},
        {TEXT("r.ScreenPercentage"), TEXT("Render scale")}, {TEXT("sg.ViewDistanceQuality"), TEXT("View distance")}};
    for (const auto& Override : Overrides)
    {
        const auto* Variable = IConsoleManager::Get().FindConsoleVariable(Override.Key);
        if (Variable && (Variable->GetFlags() & ECVF_SetByMask) > ECVF_SetByGameSetting)
            C.Notice += FString::Printf(TEXT(" %s is controlled by an engine or launch override."), Override.Value);
    }
    return C;
}

void UWarGraphicsSettings::BeginEditing()
{
    if (bPreviewing) Revert();
    if (bRecovering) return;
    Applied = Actual(); Confirmed = Applied; Draft = Applied;
    WarGraphics::Sanitize(Draft, Capabilities().MinScale, Capabilities().MaxScale);
    Message = Capabilities().Notice;
}

void UWarGraphicsSettings::RestoreDraftDefaults()
{
    Draft = FWarGraphicsSnapshot();
    const auto C = Capabilities();
    if (C.bCanChangeDisplay) Draft.Resolution = C.Desktop;
    else { Draft.Mode = Applied.Mode; Draft.Resolution = Applied.Resolution; }
    WarGraphics::Sanitize(Draft, C.MinScale, C.MaxScale);
}

void UWarGraphicsSettings::ApplySnapshot(const FWarGraphicsSnapshot& V, bool bDisplay)
{
    Write(V);
    if (bDisplay) ApplyResolutionSettings(false);
    // A synchronous resize callback may have restored serializable confirmed fields.
    Write(V);
    ApplyNonResolutionSettings();
}

bool UWarGraphicsSettings::Preview()
{
    if (bPreviewing || bRecovering) return false;
    const auto C = Capabilities();
    if (!WarGraphics::Validate(Draft, Applied, C, Message)) return false;
    Confirmed = Applied;
    ConfirmedPreferredMode = PreferredFullscreenMode;
    bPreviewing = true; bDisplayVerified = false;
    Deadline = FPlatformTime::Seconds() + 15; VerifyAfter = FPlatformTime::Seconds() + 1;
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UWarGraphicsSettings::TickPreview));
    ActivationHandle = FSlateApplication::Get().OnApplicationActivationStateChanged().AddUObject(this, &UWarGraphicsSettings::OnActivation);
    ApplySnapshot(Draft, C.bCanChangeDisplay);
    // Engine window-position saving can call SaveConfig directly. Keep serializable fields
    // confirmed even during preview; live renderer/window state remains the candidate.
    Write(Confirmed);
    PreferredFullscreenMode = ConfirmedPreferredMode;
    Message = TEXT("Checking the display. Keep changes within 15 seconds or they will revert.");
    return true;
}

int32 UWarGraphicsSettings::SecondsRemaining() const
{
    return bPreviewing ? FMath::Max(0, FMath::CeilToInt(Deadline - FPlatformTime::Seconds())) : 0;
}

bool UWarGraphicsSettings::TickPreview(float)
{
    if (bRecovering)
    {
        const auto Live = Actual();
        if (Live.Mode == Applied.Mode && Live.Resolution == Applied.Resolution) { StopPreview(); return false; }
        if (FPlatformTime::Seconds() < VerifyAfter) return true;
        const auto C = Capabilities();
        if (!bRecoveryFallback && C.bCanChangeDisplay && C.WorkArea.X > 0 && C.WorkArea.Y > 0)
        {
            bRecoveryFallback = true;
            Applied.Mode = EWindowMode::Windowed;
            Applied.Resolution = FIntPoint(FMath::Min(1280, C.WorkArea.X), FMath::Min(720, C.WorkArea.Y));
            Draft = Applied; ApplySnapshot(Applied, true);
            VerifyAfter = FPlatformTime::Seconds() + 2;
            Message = TEXT("Previous display mode was unavailable. Recovering to a window.");
            return true;
        }
        StopPreview();
        Applied = Actual(); Draft = Applied;
        Message = TEXT("The display could not restore the requested mode. Restart with -WarSafeGraphics if needed.");
        return false;
    }
    if (!bPreviewing) return false;
    const double Now = FPlatformTime::Seconds();
    if (Now >= Deadline) { Revert(TEXT("Time expired. Previous graphics restored.")); return false; }
    if (Now >= VerifyAfter)
    {
        const auto Live = Actual();
        if (Live.Mode != Draft.Mode || Live.Resolution != Draft.Resolution)
        { Revert(TEXT("The display rejected or substituted the requested mode. Previous graphics restored.")); return false; }
        bDisplayVerified = true;
    }
    return true;
}

void UWarGraphicsSettings::OnActivation(bool Active)
{
    if (!Active && bPreviewing) Revert(TEXT("Application lost focus. Previous graphics restored."));
}

void UWarGraphicsSettings::StopPreview()
{
    bPreviewing = false; bDisplayVerified = false; bRecovering = false;
    FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle); TickerHandle.Reset();
    if (FSlateApplication::IsInitialized()) FSlateApplication::Get().OnApplicationActivationStateChanged().Remove(ActivationHandle);
    ActivationHandle.Reset();
}

bool UWarGraphicsSettings::Keep()
{
    if (!CanKeep()) return false;
    const auto Live = Actual();
    if (FPlatformTime::Seconds() >= Deadline || Live.Mode != Draft.Mode || Live.Resolution != Draft.Resolution)
    { Revert(TEXT("The display changed before confirmation. Previous graphics restored.")); return false; }
    StopPreview();
    if (Draft.Mode != EWindowMode::Windowed) PreferredFullscreenMode = Draft.Mode == EWindowMode::Fullscreen ? 0 : 1;
    Write(Draft); ConfirmVideoMode(); SaveSettings();
    if (!bLastSaveSucceeded)
    {
        ApplySnapshot(Confirmed, Capabilities().bCanChangeDisplay);
        ConfirmVideoMode();
        SaveSettings(); // Restore cached/disk values too; never label this path as saved.
        Applied = Confirmed; Draft = Confirmed;
        Message = TEXT("Could not save graphics settings. Previous settings restored; check available disk space and file permissions.");
        return false;
    }
    Applied = Draft; Confirmed = Applied;
    Message = TEXT("Graphics settings saved.");
    return true;
}

void UWarGraphicsSettings::Revert(const FString& Reason)
{
    if (!bPreviewing) { Draft = Applied; return; }
    StopPreview();
    const auto C = Capabilities();
    const auto Live = Actual();
    const auto Restored = Live.Mode == Confirmed.Mode && Live.Resolution == Confirmed.Resolution
        ? Confirmed : WarGraphics::Recovery(Confirmed, C);
    if (C.bCanRender) ApplySnapshot(Restored, C.bCanChangeDisplay);
    PreferredFullscreenMode = ConfirmedPreferredMode;
    Applied = Restored; Draft = Restored;
    Message = Reason;
    if (C.bCanRender && C.bCanChangeDisplay)
    {
        bRecovering = true; bRecoveryFallback = false;
        VerifyAfter = FPlatformTime::Seconds() + 2;
        TickerHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UWarGraphicsSettings::TickPreview));
    }
}

void UWarGraphicsSettings::EndEditing()
{
    if (bPreviewing) Revert();
    Draft = Applied;
}

void UWarGraphicsSettings::BeginDestroy()
{
    EndEditing(); StopPreview();
    Super::BeginDestroy();
}
