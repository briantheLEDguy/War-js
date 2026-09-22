#include "WarGraphicsProof.h"
#include "WarGraphicsWidget.h"
#include "WarFrontendWidget.h"
#include "WarInterfaceWidget.h"
#include "WarPlayerController.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"

bool UWarGraphicsProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    // The explicit isolated ini is mandatory: this fixture must not touch player preferences.
    FString Ini;
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarGraphicsProof"))
        && FParse::Value(FCommandLine::Get(), TEXT("GameUserSettingsINI="), Ini)
        && FPaths::GetCleanFilename(Ini).StartsWith(TEXT("GraphicsProof"));
#endif
}

TStatId UWarGraphicsProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarGraphicsProof, STATGROUP_Tickables); }

void UWarGraphicsProof::Finish(bool Passed, const FString& Detail)
{
    bFinished = true;
    const FString Folder = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("GraphicsProof"));
    IFileManager::Get().MakeDirectory(*Folder, true);
    FString SafeDetail = Detail.Replace(TEXT("\\"), TEXT("\\\\")).Replace(TEXT("\""), TEXT("\\\"")).Replace(TEXT("\n"), TEXT("\\n"));
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"passed\":%s,\"step\":%d,\"detail\":\"%s\",\"manualDisplayAcceptance\":false}"),
        Passed ? TEXT("true") : TEXT("false"), Step, *SafeDetail), *FPaths::Combine(Folder, TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}

void UWarGraphicsProof::Tick(float)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = FPlatformTime::Seconds();
    if (Started == 0) Started = Now;
    if (Now - Started > 180) { Finish(false, TEXT("Graphics proof timed out")); return; }
    if (Now < NextStep) return;
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Settings = UWarGraphicsSettings::Get();
    if (!PC || !Settings) return;
    const auto Check = [this](bool Good, const FString& Detail) { if (!Good) Finish(false, Detail); return Good; };
    const auto FindWidget = [this](UClass* Class) -> UUserWidget* {
        TArray<UUserWidget*> Widgets; UWidgetBlueprintLibrary::GetAllWidgetsOfClass(GetWorld(), Widgets, Class, false);
        for (auto* Widget : Widgets) if (Widget->IsInViewport()) return Widget;
        return nullptr;
    };
    const auto Screenshot = [](const TCHAR* Name) {
        FScreenshotRequest::RequestScreenshot(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("GraphicsProof"), Name), true, false);
    };
    if (Step == 0)
    {
        const auto Folder = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("GraphicsProof"));
        if (FParse::Param(FCommandLine::Get(), TEXT("WarGraphicsProofRestart")))
        {
            FString Expected;
            const bool Read = FFileHelper::LoadFileToString(Expected, *FPaths::Combine(Folder, TEXT("interrupted-cap.txt")));
            Finish(Read && FMath::IsNearlyEqual(Settings->GetFrameRateLimit(), FCString::Atof(*Expected)),
                TEXT("Relaunch compared loaded frame cap with the baseline before forced preview exit."));
            return;
        }
        if (FParse::Param(FCommandLine::Get(), TEXT("WarGraphicsProofSafeStartup")))
        {
            const auto Live = Settings->Actual();
            Finish(Live.Mode == EWindowMode::Windowed && Live.Resolution.X <= 1280 && Live.Resolution.Y <= 720
                && Settings->GetFrameRateLimit() == 60 && WarGraphics::Preset(Settings->Capture()) == 0,
                TEXT("Safe launch checked actual initial window, conservative quality and frame cap."));
            return;
        }
        Entry = Cast<UWarFrontendWidget>(FindWidget(UWarFrontendWidget::StaticClass()));
        if (!Entry) return;
        UWarGraphicsWidget::Open(PC, Entry, true);
        Page = Cast<UWarGraphicsWidget>(FindWidget(UWarGraphicsWidget::StaticClass()));
        if (!Check(Page != nullptr, TEXT("Entry graphics page unavailable"))) return;
        Baseline = Settings->Draft;
    }
    else if (Step == 1) Screenshot(TEXT("Entry.png"));
    else if (Step == 2)
    {
        Settings->Draft.FrameLimit = Baseline.FrameLimit == 45 ? 50 : 45;
        Settings->Draft.Quality.ResolutionQuality = FMath::Max(65.f, Settings->Capabilities().MinScale);
        if (!Check(Settings->Preview(), Settings->GetMessage())) return;
    }
    else if (Step == 3)
    {
        if (!Check(Settings->CanKeep(), TEXT("Preview did not verify actual display"))) return;
        if (FParse::Param(FCommandLine::Get(), TEXT("WarGraphicsProofExit")))
        {
            const auto Folder = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("GraphicsProof"));
            IFileManager::Get().MakeDirectory(*Folder, true);
            FFileHelper::SaveStringToFile(FString::SanitizeFloat(Baseline.FrameLimit), *FPaths::Combine(Folder, TEXT("interrupted-cap.txt")));
            FPlatformMisc::RequestExitWithStatus(true, 0);
            return;
        }
        Screenshot(TEXT("Confirmation.png"));
    }
    else if (Step == 4)
    {
        if (!Check(Settings->Keep(), Settings->GetMessage())) return;
        Baseline = Settings->GetApplied();
        Settings->Draft.FrameLimit = 90;
        if (!Check(Settings->Preview(), Settings->GetMessage())) return;
        ++Step; NextStep = Now + 17; return;
    }
    else if (Step == 5)
    {
        if (!Check(!Settings->IsPreviewing() && Settings->Draft == Baseline, TEXT("Real-time rollback failed"))) return;
        FConfigFile Disk; Disk.Read(GGameUserSettingsIni); float Cap = 0;
        if (!Check(Disk.GetFloat(TEXT("/Script/AegisWar.WarGraphicsSettings"), TEXT("FrameRateLimit"), Cap) && Cap == Baseline.FrameLimit,
            TEXT("Preview leaked into saved preferences"))) return;
        Settings->Draft.FrameLimit = 75;
        if (!Check(Settings->Preview(), Settings->GetMessage())) return;
        Page->Close();
        if (!Check(!Settings->IsPreviewing() && Entry->IsInViewport(), TEXT("Closing graphics did not restore entry"))) return;
    }
    else if (Step == 6)
    {
        // Focus requests can be deferred until Slate rebuilds the path after overlay removal.
        if (!Check(Entry->HasUserFocus(PC) || Entry->HasUserFocusedDescendants(PC), TEXT("Entry keyboard focus was not restored"))) return;
        PC->ServerCreateDevelopmentCharacter(TEXT("Graphics Tester"), TEXT("empire"), TEXT("battle_prelate"), TEXT("m"));
    }
    else if (Step == 7)
    {
        if (!PC->GetPawn()) return;
        PC->ShowInterface(TEXT("Options"));
        auto* Options = FindWidget(UWarInterfaceWidget::StaticClass());
        if (!Check(Options != nullptr, TEXT("In-game Options unavailable"))) return;
        UWarGraphicsWidget::Open(PC, Options, false);
        Page = Cast<UWarGraphicsWidget>(FindWidget(UWarGraphicsWidget::StaticClass()));
        if (!Check(Page != nullptr, TEXT("In-game graphics page unavailable"))) return;
    }
    else if (Step == 8) Screenshot(TEXT("InGame.png"));
    else if (Step == 9)
    {
        const auto Caps = Settings->Capabilities();
        bool Found = false;
        for (const auto Resolution : Caps.WindowedResolutions)
            if (Resolution != Settings->Draft.Resolution) { Settings->Draft.Resolution = Resolution; Found = true; break; }
        if (!Check(Found, TEXT("No alternate window size available for proof"))) return;
        Settings->Draft.Mode = EWindowMode::Windowed;
        if (!Check(Settings->Preview(), Settings->GetMessage())) return;
    }
    else if (Step == 10)
    {
        if (!Check(Settings->CanKeep(), TEXT("Window resize was rejected"))) return;
        Screenshot(TEXT("Resized.png"));
    }
    else if (Step == 11) Settings->Revert();
    else if (Step == 12)
    {
        const auto Live = Settings->Actual();
        if (!Check(Live.Resolution == Baseline.Resolution && Live.Mode == Baseline.Mode, TEXT("Window rollback did not restore actual size"))) return;
        Page->Close();
        if (!Check(PC->IsInterfaceOpen() && PC->IsMoveInputIgnored(), TEXT("Options input lock not restored"))) return;
        Finish(true, TEXT("Entry and game pages rendered; confirmation, persistence, timeout, closure, resize and rollback passed."));
        return;
    }
    ++Step; NextStep = Now + 2;
}
