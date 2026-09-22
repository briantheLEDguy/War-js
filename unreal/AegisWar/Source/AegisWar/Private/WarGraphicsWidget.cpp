#include "WarGraphicsWidget.h"
#include "WarGraphicsSettings.h"
#include "WarInterfaceStyle.h"
#include "WarMenuFrame.h"
#include "GameFramework/PlayerController.h"
#include "Engine/LocalPlayer.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/STextComboBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SSlider.h"

void UWarGraphicsWidget::Open(APlayerController* PC, UUserWidget* ReturnTo, bool Entry)
{
    if (!PC || !PC->IsLocalController() || !PC->GetLocalPlayer() || !ReturnTo || !UWarGraphicsSettings::Get()) return;
    auto* Widget = CreateWidget<UWarGraphicsWidget>(PC);
    Widget->Settings = UWarGraphicsSettings::Get();
    if (ReturnTo->HasUserFocus(PC) || ReturnTo->HasUserFocusedDescendants(PC))
    {
        const auto User = FSlateApplication::Get().GetUserIndexForController(PC->GetLocalPlayer()->GetControllerId());
        if (User >= 0) Widget->PreviousFocus = FSlateApplication::Get().GetUserFocusedWidget(User);
    }
    Widget->ReturnWidget = ReturnTo; Widget->bReturnToEntry = Entry;
    Widget->Settings->BeginEditing();
    Widget->AddToViewport(300);
    FInputModeUIOnly Mode; Mode.SetWidgetToFocus(Widget->TakeWidget());
    PC->SetInputMode(Mode); PC->bShowMouseCursor = true;
    Widget->SetUserFocus(PC);
}

void UWarGraphicsWidget::Close()
{
    Settings->EndEditing();
    RemoveFromParent();
    if (auto* PC = GetOwningPlayer(); PC && PC->GetLocalPlayer() && ReturnWidget && ReturnWidget->IsInViewport())
    {
        const auto Focus = PreviousFocus.IsValid() ? PreviousFocus.Pin().ToSharedRef() : ReturnWidget->TakeWidget();
        if (bReturnToEntry)
        { FInputModeUIOnly Mode; Mode.SetWidgetToFocus(Focus); PC->SetInputMode(Mode); }
        else
        { FInputModeGameAndUI Mode; Mode.SetWidgetToFocus(Focus); Mode.SetHideCursorDuringCapture(false); PC->SetInputMode(Mode); }
        if (!PreviousFocus.IsValid()) ReturnWidget->SetUserFocus(PC);
        else if (const auto User = FSlateApplication::Get().GetUserIndexForController(PC->GetLocalPlayer()->GetControllerId()); User >= 0)
            if (FSlateApplication::Get().SetUserFocus(User, Focus, EFocusCause::SetDirectly))
                PC->GetLocalPlayer()->GetSlateOperations().CancelFocusRequest();
        PC->bShowMouseCursor = true;
    }
}

void UWarGraphicsWidget::NativeDestruct()
{
    if (Settings) Settings->EndEditing();
    Super::NativeDestruct();
}

void UWarGraphicsWidget::ReleaseSlateResources(bool Children)
{
    Super::ReleaseSlateResources(Children); Controls.Reset();
}

FReply UWarGraphicsWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape)
    {
        if (Settings->IsPreviewing()) { Settings->Revert(); Refresh(); }
        else Close();
        return FReply::Handled();
    }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}

void UWarGraphicsWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    if (!ReturnWidget || !ReturnWidget->IsInViewport()) { Close(); return; }
    if (bWasPreviewing != Settings->IsPreviewing()) { bWasPreviewing = Settings->IsPreviewing(); Refresh(); }
    // Refresh display lists when the OS reports a different monitor arrangement. Do not
    // rebuild focused sliders every frame or silently replace a user's draft selection.
    if (FPlatformTime::Seconds() >= NextRefresh && !Settings->IsPreviewing())
    {
        NextRefresh = FPlatformTime::Seconds() + 2;
        const auto C = Settings->Capabilities();
        FString Key = FString::Printf(TEXT("%d:%d:%d:%d:%d:%d"), C.Desktop.X, C.Desktop.Y, C.WorkArea.X, C.WorkArea.Y,
            C.bFullscreen, C.bCanChangeDisplay);
        for (const auto R : C.FullscreenResolutions) Key += FString::Printf(TEXT("f%d,%d;"), R.X, R.Y);
        for (const auto R : C.WindowedResolutions) Key += FString::Printf(TEXT("w%d,%d;"), R.X, R.Y);
        if (Key != DisplayKey) { DisplayKey = Key; Refresh(); }
    }
}

TSharedRef<SWidget> UWarGraphicsWidget::RebuildWidget()
{
    SetIsFocusable(true);
    auto Button = [this](const TCHAR* Label, TFunction<void()> Action, TAttribute<bool> Enabled, TAttribute<EVisibility> ButtonVisibility) {
        return SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(FMargin(14, 10))
            .IsEnabled(Enabled).Visibility(ButtonVisibility).OnClicked_Lambda([Action] { Action(); return FReply::Handled(); })
            [SNew(STextBlock).Text(FText::FromString(Label)).Font(FCoreStyle::GetDefaultFontStyle("Bold", 14))];
    };
    const auto Editing = TAttribute<EVisibility>::CreateLambda([this] { return Settings->IsPreviewing() ? EVisibility::Collapsed : EVisibility::Visible; });
    const auto Previewing = TAttribute<EVisibility>::CreateLambda([this] { return Settings->IsPreviewing() ? EVisibility::Visible : EVisibility::Collapsed; });
    auto Root = SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.005f,0.008f,0.012f,0.98f)).Padding(16)
        [SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly)
            [SNew(SBox).WidthOverride(960).HeightOverride(760)
                [SNew(SWarMenuFrame)
                    [SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
                            [SNew(STextBlock).Text(FText::FromString(TEXT("Graphics"))).ColorAndOpacity(WarInterfaceStyle::Gold).Font(FCoreStyle::GetDefaultFontStyle("Bold", 28))]
                        + SVerticalBox::Slot().FillHeight(1)
                            [SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Controls, SVerticalBox).IsEnabled_Lambda([this] { return !Settings->IsPreviewing() && !Settings->IsRecovering(); })]]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 10)
                            [SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).ColorAndOpacity(WarInterfaceStyle::Gold).Text_Lambda([this] {
                                return FText::FromString(Settings->GetMessage() + (Settings->IsPreviewing() ? FString::Printf(TEXT("\nReverting in %d seconds."), Settings->SecondsRemaining()) : TEXT(""))); })]
                        + SVerticalBox::Slot().AutoHeight()
                            [SNew(SHorizontalBox)
                                + SHorizontalBox::Slot().AutoWidth().Padding(0,0,8,0)[Button(TEXT("Apply"), [this] { Settings->Preview(); },
                                    TAttribute<bool>::CreateLambda([this] { return !Settings->IsRecovering() && !(Settings->Draft == Settings->GetApplied()); }), Editing)]
                                + SHorizontalBox::Slot().AutoWidth().Padding(0,0,8,0)[Button(TEXT("Cancel / Back"), [this] { Close(); }, true, Editing)]
                                + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Restore Defaults"), [this] { Settings->RestoreDraftDefaults(); Refresh(); },
                                    TAttribute<bool>::CreateLambda([this] { return !Settings->IsRecovering(); }), Editing)]
                                + SHorizontalBox::Slot().AutoWidth().Padding(0,0,8,0)[Button(TEXT("Keep changes"), [this] { Settings->Keep(); Refresh(); },
                                    TAttribute<bool>::CreateLambda([this] { return Settings->CanKeep(); }), Previewing)]
                                + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Revert"), [this] { Settings->Revert(); Refresh(); }, true, Previewing)]]]]]];
    Refresh();
    return Root;
}

void UWarGraphicsWidget::Refresh()
{
    if (!Controls || !Settings) return;
    Controls->ClearChildren();
    const auto C = Settings->Capabilities();
    const auto Label = [this](const FString& Text) {
        Controls->AddSlot().AutoHeight().Padding(0, 6)[SNew(STextBlock).Text(FText::FromString(Text)).AutoWrapText(true)
            .ColorAndOpacity(WarInterfaceStyle::Text).Font(FCoreStyle::GetDefaultFontStyle("Regular", 15))];
    };
    const auto Combo = [this, Label](const FString& Name, const TArray<FString>& Values, const FString& Selected, TFunction<void(int32)> Change, bool Enabled = true) {
        Label(Name);
        auto Items = MakeShared<TArray<TSharedPtr<FString>>>(); TSharedPtr<FString> Initial;
        for (const auto& Value : Values) { auto Item = MakeShared<FString>(Value); Items->Add(Item); if (Value == Selected) Initial = Item; }
        Controls->AddSlot().AutoHeight().Padding(0,0,0,6)
            [SNew(STextComboBox).OptionsSource(&Items.Get()).InitiallySelectedItem(Initial).IsEnabled(Enabled)
                .ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(FMargin(12,6)).Font(FCoreStyle::GetDefaultFontStyle("Regular", 15))
                .OnSelectionChanged_Lambda([Items, Change](TSharedPtr<FString> Item, ESelectInfo::Type Type) { if (Item && Type != ESelectInfo::Direct) Change(Items->IndexOfByKey(Item)); })];
    };
    Label(TEXT("Choose a preset, then adjust for your PC. Changes are previewed until you choose Keep changes."));
    if (!C.Notice.IsEmpty()) Label(C.Notice);
    TArray<EWindowMode::Type> Modes{EWindowMode::Windowed, EWindowMode::WindowedFullscreen};
    TArray<FString> ModeNames{TEXT("Windowed"), TEXT("Borderless Fullscreen")};
    if (C.bFullscreen || Settings->Draft.Mode == EWindowMode::Fullscreen) { Modes.Add(EWindowMode::Fullscreen); ModeNames.Add(TEXT("Fullscreen")); }
    const int32 ModeIndex = Modes.IndexOfByKey(Settings->Draft.Mode);
    Combo(TEXT("Display mode"), ModeNames, ModeNames.IsValidIndex(ModeIndex) ? ModeNames[ModeIndex] : TEXT(""), [this, Modes](int32 I) {
        const auto Caps = Settings->Capabilities(); Settings->Draft.Mode = Modes[I];
        const auto& Values = Modes[I] == EWindowMode::Fullscreen ? Caps.FullscreenResolutions : Caps.WindowedResolutions;
        if (Modes[I] == EWindowMode::WindowedFullscreen) Settings->Draft.Resolution = Caps.Desktop;
        else Settings->Draft.Resolution = WarGraphics::PickResolution(Settings->Draft.Resolution, Values);
        Refresh();
    }, C.bCanChangeDisplay);
    auto Resolutions = Settings->Draft.Mode == EWindowMode::Fullscreen ? C.FullscreenResolutions : C.WindowedResolutions;
    if (Settings->Draft.Mode == EWindowMode::WindowedFullscreen) Resolutions = {C.Desktop};
    Resolutions.AddUnique(Settings->Draft.Resolution);
    TArray<FString> ResolutionNames;
    for (const auto P : Resolutions) ResolutionNames.Add(FString::Printf(TEXT("%d x %d"), P.X, P.Y));
    Combo(TEXT("Resolution"), ResolutionNames, FString::Printf(TEXT("%d x %d"), Settings->Draft.Resolution.X, Settings->Draft.Resolution.Y),
        [this, Resolutions](int32 I) { Settings->Draft.Resolution = Resolutions[I]; },
        C.bCanChangeDisplay && Settings->Draft.Mode != EWindowMode::WindowedFullscreen && Resolutions.Num() > 1);
    if (Settings->Draft.Mode == EWindowMode::WindowedFullscreen) Label(TEXT("Borderless fills the desktop. Lower render scale to reduce 3D rendering work; menus stay sharp."));
    TArray<FString> QualityNames{TEXT("Low"), TEXT("Medium"), TEXT("High"), TEXT("Epic"), TEXT("Custom")};
    const int32 Preset = WarGraphics::Preset(Settings->Draft);
    if (Preset >= 0) QualityNames.SetNum(4);
    Combo(TEXT("Quality preset - lower settings reduce rendering work"), QualityNames, QualityNames[Preset < 0 ? 4 : Preset],
        [this](int32 I) { if (I < 4) WarGraphics::SetPreset(Settings->Draft, I); Refresh(); });
    Controls->AddSlot().AutoHeight().Padding(0,8)[SNew(SCheckBox)
        .IsChecked_Lambda([this] { return Settings->Draft.bVSync ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
        .OnCheckStateChanged_Lambda([this](ECheckBoxState S) { Settings->Draft.bVSync = S == ECheckBoxState::Checked; })
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).ColorAndOpacity(WarInterfaceStyle::Text).Text(FText::FromString(TEXT("VSync - reduce screen tearing; may increase input delay")))]];
    const auto Slider = [this](const FString& Name, float Min, float Max, TFunction<float()> Get, TFunction<void(float)> Set) {
        Controls->AddSlot().AutoHeight().Padding(0,8,0,4)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).ColorAndOpacity(WarInterfaceStyle::Text)
            .Text_Lambda([Name, Get] { return FText::FromString(FString::Printf(TEXT("%s: %.0f"), *Name, Get())); })];
        Controls->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(SSlider).MinValue(Min).MaxValue(Max).StepSize(1).MouseUsesStep(true)
            .SliderHandleColor(WarInterfaceStyle::Gold).Value_Lambda([Get] { return Get(); })
            .OnValueChanged_Lambda([Set](float V) { Set(FMath::RoundToFloat(V)); })];
    };
    Slider(TEXT("Frame cap (FPS)"), 30, 240, [this] { return Settings->Draft.FrameLimit; }, [this](float V) { Settings->Draft.FrameLimit = V; });
    Slider(TEXT("Render scale (%)"), C.MinScale, C.MaxScale, [this] { return Settings->Draft.Quality.ResolutionQuality; }, [this](float V) { Settings->Draft.Quality.ResolutionQuality = V; });
    Combo(TEXT("View distance - distant scenery detail"), {TEXT("Near"), TEXT("Medium"), TEXT("Far"), TEXT("Epic")},
        TArray<FString>{TEXT("Near"), TEXT("Medium"), TEXT("Far"), TEXT("Epic")}[FMath::Clamp(Settings->Draft.Quality.ViewDistanceQuality, 0, 3)],
        [this](int32 I) { Settings->Draft.Quality.ViewDistanceQuality = I; Refresh(); });
    // NativeTick can rebuild after Slate's normal prepass. Measure the new controls
    // before painting so resize/recovery never draws zero-height overlapping rows.
    ForceLayoutPrepass();
}
