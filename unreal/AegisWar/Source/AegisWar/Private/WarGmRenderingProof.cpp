#include "WarInterfaceProof.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarInterfaceWidget.h"
#include "WarZoneLightingSubsystem.h"
#include "WarZoneAnchor.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LevelStreaming.h"
#include "Engine/PostProcessVolume.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Application/ThrottleManager.h"
#include "Framework/Application/SlateApplication.h"
#include "Layout/WidgetPath.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/SWindow.h"
#include "UObject/UObjectIterator.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "UnrealClient.h"
#include "TimerManager.h"

namespace
{
    void PressGameKey(AWarPlayerController* PC, const FKey Key)
    {
        // Exercise engine debug exec as well as the normal accumulated gameplay
        // event. Desktop manual runs separately cover OS/Slate focus and routing.
        PC->InputKey(FInputKeyEventArgs(nullptr, INPUTDEVICEID_NONE, Key, IE_Pressed, FPlatformTime::Cycles64()));
        FTimerHandle Release;
        PC->GetWorld()->GetTimerManager().SetTimer(Release, FTimerDelegate::CreateWeakLambda(PC, [PC, Key] {
            PC->InputKey(FInputKeyEventArgs(nullptr, INPUTDEVICEID_NONE, Key, IE_Released, FPlatformTime::Cycles64()));
        }), .25f, false);
    }

    TSharedPtr<SWidget> FindControl(const TSharedRef<SWidget>& Root, const FString& Label)
    {
        if (Label == TEXT("speed") && Root->GetTypeAsString() == TEXT("SSlider")) return Root;
        if (Root->GetTypeAsString() == TEXT("SButton"))
        {
            const auto Content = StaticCastSharedRef<SButton>(Root)->GetContent();
            if (Content->GetTypeAsString() == TEXT("STextBlock") && StaticCastSharedRef<STextBlock>(Content)->GetText().ToString() == Label) return Root;
        }
        auto* Children = Root->GetChildren();
        for (int32 I = 0; Children && I < Children->Num(); ++I)
            if (auto Found = FindControl(Children->GetChildAt(I), Label)) return Found;
        return nullptr;
    }

    bool PointerCommand(AWarPlayerController* PC, const FString& Label, float Fraction = .5f)
    {
        TSharedPtr<SWidget> Control;
        for (TObjectIterator<UWarInterfaceWidget> It; It; ++It)
            if (It->GetOwningPlayer() == PC && It->IsInViewport()) Control = FindControl(It->TakeWidget(), Label);
        if (!Control || !Control->IsEnabled()) return false;
        auto& Slate = FSlateApplication::Get();
        FWidgetPath Path;
        if (!Slate.GeneratePathToWidgetUnchecked(Control.ToSharedRef(), Path) || !Path.IsValid()) return false;
        TArray<FWidgetAndPointer> Entries;
        for (int32 Index = 0; Index < Path.Widgets.Num(); ++Index) Entries.Emplace(Path.Widgets[Index]);
        Path = FWidgetPath(MakeArrayView(Entries));
        const auto& Geometry = Control->GetCachedGeometry();
        const FVector2D Start = Geometry.LocalToAbsolute(Geometry.GetLocalSize() * .5f);
        const FVector2D End = Geometry.LocalToAbsolute(FVector2D(Geometry.GetLocalSize().X * Fraction, Geometry.GetLocalSize().Y * .5));
        const uint32 Pointer = FSlateApplication::CursorPointerIndex;
        const TSet<FKey> Pressed{EKeys::LeftMouseButton};
        if (FParse::Param(FCommandLine::Get(), TEXT("WarGmRenderingHitTest")))
        {
            Slate.ProcessMouseMoveEvent(FPointerEvent(Pointer, Start, Start, {}, EKeys::Invalid, 0, FModifierKeysState()), false);
            Slate.ProcessMouseButtonDownEvent(Path.GetWindow()->GetNativeWindow(), FPointerEvent(Pointer, Start, Start, Pressed, EKeys::LeftMouseButton, 0, FModifierKeysState()));
            if (!Control->HasMouseCapture())
            {
                Slate.ProcessMouseButtonUpEvent(FPointerEvent(Pointer, Start, Start, {}, EKeys::LeftMouseButton, 0, FModifierKeysState()));
                return false;
            }
            // Hold across rendered frames so normal Slate responsiveness throttling participates.
            FTimerHandle Release;
            PC->GetWorld()->GetTimerManager().SetTimer(Release, FTimerDelegate::CreateLambda([Start, End, Pointer, Pressed] {
                auto& App = FSlateApplication::Get();
                App.ProcessMouseMoveEvent(FPointerEvent(Pointer, End, Start, Pressed, EKeys::Invalid, 0, FModifierKeysState()), false);
                App.ProcessMouseButtonUpEvent(FPointerEvent(Pointer, End, End, {}, EKeys::LeftMouseButton, 0, FModifierKeysState()));
            }), .5f, false);
            return true;
        }
        // Mouse-up clicks require Slate's hover path as well as pointer capture.
        Slate.RoutePointerMoveEvent(Path, FPointerEvent(Pointer, Start, Start, {}, EKeys::Invalid, 0, FModifierKeysState()), false);
        Slate.RoutePointerDownEvent(Path, FPointerEvent(Pointer, Start, Start, Pressed, EKeys::LeftMouseButton, 0, FModifierKeysState()));
        if (Label == TEXT("speed")) Slate.RoutePointerMoveEvent(Path, FPointerEvent(Pointer, End, Start, Pressed, EKeys::Invalid, 0, FModifierKeysState()), false);
        Slate.RoutePointerUpEvent(Path, FPointerEvent(Pointer, End, End, {}, EKeys::LeftMouseButton, 0, FModifierKeysState()));
        return true;
    }

    void Capture(AWarPlayerController* PC, const FString& Folder, const FString& Name)
    {
        auto Root = MakeShared<FJsonObject>();
        Root->SetStringField(TEXT("step"), Name);
        Root->SetNumberField(TEXT("time"), PC->GetWorld()->GetTimeSeconds());
        Root->SetBoolField(TEXT("allowsExpensiveTasks"), FSlateThrottleManager::Get().IsAllowingExpensiveTasks());
        Root->SetStringField(TEXT("position"), PC->GetPawn()->GetActorLocation().ToString());
        Root->SetStringField(TEXT("camera"), PC->PlayerCameraManager->GetCameraLocation().ToString());
        Root->SetStringField(TEXT("cameraRotation"), PC->PlayerCameraManager->GetCameraRotation().ToString());
        Root->SetStringField(TEXT("zone"), PC->GetWorld()->GetSubsystem<UWarZoneLightingSubsystem>()->GetActiveZone().ToString());
        const auto* Character = Cast<AWarCharacter>(PC->GetPawn());
        Root->SetBoolField(TEXT("flying"), Character->IsDevelopmentFlying());
        Root->SetNumberField(TEXT("speed"), Character->GetDevelopmentSpeed());
        auto Variables = MakeShared<FJsonObject>();
        for (const TCHAR* Key : {TEXT("sg.GlobalIlluminationQuality"), TEXT("sg.ReflectionQuality"), TEXT("sg.PostProcessQuality"), TEXT("sg.ShadowQuality"), TEXT("sg.EffectsQuality"), TEXT("sg.TextureQuality"), TEXT("sg.ResolutionQuality"), TEXT("r.EyeAdaptationQuality"), TEXT("r.Tonemapper.Quality"), TEXT("r.TonemapperGamma"), TEXT("r.Color.Mid"), TEXT("r.Color.Min"), TEXT("r.Color.Max"), TEXT("r.ScreenPercentage"), TEXT("r.HDR.EnableHDROutput"), TEXT("r.SkyLight.RealTimeReflectionCapture"), TEXT("r.Lumen.DiffuseIndirect.Allow"), TEXT("r.Lumen.Reflections.Allow")})
            if (const auto* Var = IConsoleManager::Get().FindConsoleVariable(Key)) Variables->SetStringField(Key, Var->GetString());
        Root->SetObjectField(TEXT("renderer"), Variables);
        Root->SetNumberField(TEXT("displayGamma"), GEngine->GetDisplayGamma());
        FString Flags;
        if (GEngine->GameViewport)
        {
            Flags = GEngine->GameViewport->EngineShowFlags.ToString();
            Root->SetNumberField(TEXT("viewMode"), GEngine->GameViewport->ViewModeIndex);
        }
        Root->SetStringField(TEXT("showFlags"), Flags);
        auto Components = MakeShared<FJsonObject>();
        for (TObjectIterator<USceneComponent> It; It; ++It)
        {
            if (It->GetWorld() != PC->GetWorld() || !It->IsRegistered()) continue;
            const auto* Light = Cast<ULightComponent>(*It);
            const auto* Sky = Cast<USkyLightComponent>(*It);
            const auto* Grade = Cast<UPostProcessComponent>(*It);
            if (!Light && !Sky && !Grade) continue;
            auto Row = MakeShared<FJsonObject>();
            Row->SetBoolField(TEXT("visible"), It->IsVisible());
            Row->SetBoolField(TEXT("hiddenInGame"), It->bHiddenInGame);
            if (Light) Row->SetNumberField(TEXT("intensity"), Light->Intensity);
            if (Sky) { Row->SetNumberField(TEXT("intensity"), Sky->Intensity); Row->SetBoolField(TEXT("realTime"), Sky->bRealTimeCapture); }
            if (Grade) { Row->SetBoolField(TEXT("enabled"), Grade->bEnabled); Row->SetNumberField(TEXT("saturation"), Grade->Settings.ColorSaturation.X); Row->SetNumberField(TEXT("exposure"), Grade->Settings.AutoExposureBias); }
            Components->SetObjectField(It->GetPathName(), Row);
        }
        Root->SetObjectField(TEXT("components"), Components);
        auto Volumes = MakeShared<FJsonObject>();
        for (TActorIterator<APostProcessVolume> It(PC->GetWorld()); It; ++It)
        {
            auto Row = MakeShared<FJsonObject>();
            Row->SetBoolField(TEXT("enabled"), It->bEnabled);
            Row->SetBoolField(TEXT("unbound"), It->bUnbound);
            Row->SetNumberField(TEXT("weight"), It->BlendWeight);
            Row->SetNumberField(TEXT("priority"), It->Priority);
            Row->SetNumberField(TEXT("saturation"), It->Settings.ColorSaturation.X);
            Row->SetNumberField(TEXT("exposure"), It->Settings.AutoExposureBias);
            Volumes->SetObjectField(It->GetPathName(), Row);
        }
        Root->SetObjectField(TEXT("postProcessVolumes"), Volumes);
        const auto& View = PC->PlayerCameraManager->GetCameraCacheView();
        auto Camera = MakeShared<FJsonObject>();
        Camera->SetNumberField(TEXT("blendWeight"), View.PostProcessBlendWeight);
        Camera->SetNumberField(TEXT("saturation"), View.PostProcessSettings.ColorSaturation.X);
        Camera->SetNumberField(TEXT("exposure"), View.PostProcessSettings.AutoExposureBias);
        Camera->SetNumberField(TEXT("fov"), View.FOV);
        Root->SetObjectField(TEXT("cameraPostProcess"), Camera);
        auto Levels = MakeShared<FJsonObject>();
        for (auto* Level : PC->GetWorld()->GetStreamingLevels()) if (Level) Levels->SetBoolField(Level->GetWorldAssetPackageName(), Level->IsLevelVisible());
        Root->SetObjectField(TEXT("levels"), Levels);
        FString Json; FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json, *(Folder / (Name + TEXT(".json"))));
        FScreenshotRequest::RequestScreenshot(Folder / (Name + TEXT(".png")), true, false);
        // Keep the final Slate-composited image as well as the underlying scene:
        // a persistent UI tint would be invisible in a scene-only screenshot.
        FTimerHandle SceneCapture;
        PC->GetWorld()->GetTimerManager().SetTimer(SceneCapture, FTimerDelegate::CreateLambda([Folder, Name] {
            FScreenshotRequest::RequestScreenshot(Folder / (Name + TEXT("-scene.png")), false, false);
        }), .25f, false);
    }
}

void UWarInterfaceProof::TickGmRendering(double Now)
{
    FString Run, Ini; FGuid Id;
    if (!FParse::Value(FCommandLine::Get(), TEXT("WarProofDraftId="), Run) || !FGuid::Parse(Run, Id)
        || !FParse::Value(FCommandLine::Get(), TEXT("GameUserSettingsINI="), Ini) || !FPaths::GetCleanFilename(Ini).StartsWith(TEXT("GmRenderingProof")))
    { Finish(false, TEXT("GM rendering proof requires isolated preferences and draft ID")); return; }
    const FString Folder = FPaths::ProjectSavedDir() / TEXT("GmRenderingProof") / Id.ToString(EGuidFormats::Digits);
    IFileManager::Get().MakeDirectory(*Folder, true);
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn = Cast<AWarCharacter>(PC->GetPawn());
    const bool Direct = FParse::Param(FCommandLine::Get(), TEXT("WarGmRenderingDirect"));
    const bool Idle = FParse::Param(FCommandLine::Get(), TEXT("WarGmRenderingIdle"));
    const bool Keyboard = FParse::Param(FCommandLine::Get(), TEXT("WarGmRenderingKeyboard"));
    if (Step == 0 && Now < 35)
    {
        Capture(PC, Folder, FString::Printf(TEXT("warmup-%02d"), FMath::FloorToInt(Now)));
        NextStep = Now + 5; return;
    }
    if (FParse::Param(FCommandLine::Get(), TEXT("WarGmRenderingManual")))
    {
        if (IFileManager::Get().FileExists(*(Folder / TEXT("stop.txt"))))
        { Finish(true, TEXT("Manual diagnostic capture stopped; visual acceptance requires inspection")); return; }
        // PIE reserves Escape for ending play. The isolated fixture can open the
        // same menu without changing the owner's editor keyboard preferences.
        const FString OpenMenu = Folder / TEXT("open-menu.txt");
        if (Step > 0 && IFileManager::Get().FileExists(*OpenMenu))
        {
            PC->ShowInterface(TEXT("Menu"));
            IFileManager::Get().Delete(*OpenMenu);
        }
        Capture(PC, Folder, Step == 0 ? TEXT("00-baseline") : FString::Printf(TEXT("%03d-manual"), Step));
        ++Step; NextStep = Now + 5; return;
    }
    FString Label;
    switch (Step)
    {
    case 0: BuilderStart = Pawn->GetActorLocation(); Label = TEXT("00-baseline"); break;
    case 1:
        if (Keyboard) PressGameKey(PC, EKeys::F2);
        else if (!Idle && !Direct) PC->ShowInterface(TEXT("GM Tools"));
        Label = TEXT("01-open"); break;
    case 2:
        if (!Idle) { if (Direct) PC->ServerSetDevelopmentTraversal(true, 1); else if (!PointerCommand(PC, TEXT("Fly / walk"))) { Finish(false, TEXT("Flight control missing")); return; } }
        Label = TEXT("02-flight"); break;
    case 3:
        if (!Idle && !Pawn->IsDevelopmentFlying()) { Finish(false, TEXT("Flight interaction did not execute")); return; }
        PC->CloseAllPanels(); Label = TEXT("03-closed"); break;
    case 4: Label = TEXT("04-settled"); break;
    case 5:
        if (Keyboard) PressGameKey(PC, EKeys::F2);
        else if (!Idle && !Direct) PC->ShowInterface(TEXT("GM Tools"));
        break;
    case 6:
        if (!Idle) { if (Direct) PC->ServerSetDevelopmentTraversal(true, 6); else if (!PointerCommand(PC, TEXT("speed"), 1)) { Finish(false, TEXT("Speed control missing")); return; } }
        Label = TEXT("06-speed"); break;
    case 7:
        if (!Idle && !FMath::IsNearlyEqual(Pawn->GetDevelopmentSpeed(), 6.f)) { Finish(false, TEXT("Speed interaction did not execute")); return; }
        PC->CloseAllPanels(); Label = TEXT("07-speed-closed"); break;
    case 8: if (!Idle) PC->ServerReturnToDevelopmentSpawn(); Label = TEXT("08-return"); break;
    case 9: if (!Idle) PC->ServerSetDevelopmentTraversal(false, 1); Label = TEXT("09-walking"); break;
    case 10: Label = TEXT("10-final"); break;
    case 11:
        if (!Idle) PC->ServerGmTeleportZone(TEXT("sunmeadow_march"));
        BuilderObjectCount = FMath::FloorToInt(Now); Label = TEXT("11-departure"); break;
    case 12:
        if (!Idle && GetWorld()->GetSubsystem<UWarZoneLightingSubsystem>()->GetActiveZone() != TEXT("sunmeadow_march"))
        {
            if (Now - BuilderObjectCount > 40) { Finish(false, TEXT("GM destination did not become ready")); return; }
            NextStep = Now + 1; return;
        }
        Label = TEXT("12-destination"); break;
    case 13:
        if (!Idle) PC->ServerGmTeleportZone(TEXT("aegis_capital"));
        BuilderObjectCount = FMath::FloorToInt(Now); Label = TEXT("13-return-pending"); break;
    case 14:
        if (!Idle && GetWorld()->GetSubsystem<UWarZoneLightingSubsystem>()->GetActiveZone() != TEXT("aegis_capital"))
        {
            if (Now - BuilderObjectCount > 40) { Finish(false, TEXT("GM capital return did not become ready")); return; }
            NextStep = Now + 1; return;
        }
        Label = TEXT("14-capital"); break;
    case 15: if (!Idle) PC->ServerReturnToDevelopmentSpawn(); break;
    case 16: Label = TEXT("16-roundtrip"); break;
    case 17: Label = TEXT("17-roundtrip-settled"); break;
    case 18:
        if (!Keyboard) { Finish(true, TEXT("GM rendering diagnostics captured; visual acceptance requires inspection")); return; }
        PressGameKey(PC, EKeys::F1); Label = TEXT("18-guide"); break;
    case 19: PC->CloseAllPanels(); Label = TEXT("19-guide-closed"); break;
    case 20: PressGameKey(PC, EKeys::F3); Label = TEXT("20-f3"); break;
    case 21: PressGameKey(PC, EKeys::F4); Label = TEXT("21-f4"); break;
    case 22: PressGameKey(PC, EKeys::F5); Label = TEXT("22-f5"); break;
    case 23: Label = TEXT("23-keyboard-settled"); break;
    default:
        Finish(true, TEXT("GM rendering diagnostics captured; compare images and state before claiming visual acceptance")); return;
    }
    if (!Label.IsEmpty()) Capture(PC, Folder, Label);
    ++Step; NextStep = Now + 5;
}
