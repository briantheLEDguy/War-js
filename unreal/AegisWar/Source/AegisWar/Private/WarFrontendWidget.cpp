#include "WarFrontendWidget.h"
#include "WarFrontendPresentation.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SWindow.h"
#include "Widgets/Input/SCheckBox.h"
#include "WarDevelopmentAccount.h"
#include "Engine/GameInstance.h"
#include "Kismet/KismetSystemLibrary.h"
#include "WarGraphicsWidget.h"
#include "Materials/MaterialInterface.h"
#include "WarPlayerController.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SComboBox.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Widgets/Layout/SScaleBox.h"

namespace
{
    class SFrontendCharacter : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SFrontendCharacter) {} SLATE_DEFAULT_SLOT(FArguments, Content) SLATE_END_ARGS()
        void Construct(const FArguments& Args, UWarFrontendPresentation* InPresentation)
        { Presentation = InPresentation; ChildSlot[Args._Content.Widget]; }
        virtual bool SupportsKeyboardFocus() const override { return true; }
        virtual FReply OnMouseButtonDown(const FGeometry&, const FPointerEvent& Event) override
        {
            if (Event.GetEffectingButton() == EKeys::LeftMouseButton && Presentation.IsValid() && Presentation->HasCharacter())
                return FReply::Handled().CaptureMouse(SharedThis(this)).SetUserFocus(SharedThis(this));
            return FReply::Unhandled();
        }
        virtual FReply OnMouseButtonUp(const FGeometry&, const FPointerEvent& Event) override
        { return Event.GetEffectingButton() == EKeys::LeftMouseButton && HasMouseCapture() ? FReply::Handled().ReleaseMouseCapture() : FReply::Unhandled(); }
        virtual FReply OnMouseMove(const FGeometry&, const FPointerEvent& Event) override
        {
            if (!HasMouseCapture() || !Presentation.IsValid()) return FReply::Unhandled();
            Presentation->Rotate(Event.GetCursorDelta().X * .4f); return FReply::Handled();
        }
        virtual FReply OnKeyDown(const FGeometry&, const FKeyEvent& Event) override
        {
            if (!Presentation.IsValid()) return FReply::Unhandled();
            if (Event.GetKey() == EKeys::Left || Event.GetKey() == EKeys::Right)
            { Presentation->Rotate(Event.GetKey() == EKeys::Left ? -10 : 10); return FReply::Handled(); }
            if (Event.GetKey() == EKeys::Home) { Presentation->ResetRotation(); return FReply::Handled(); }
            return FReply::Unhandled();
        }
    private:
        TWeakObjectPtr<UWarFrontendPresentation> Presentation;
    };
    const FLinearColor Gold(0.72f, 0.49f, 0.21f);
    const FLinearColor Ivory(0.91f, 0.86f, 0.74f);
    const FLinearColor Muted(0.58f, 0.49f, 0.36f);
    const FLinearColor Ink(0.022f, 0.016f, 0.010f);

    const FSlateBrush* CharacterBackdrop()
    {
        static const FSlateRoundedBoxBrush Brush(FLinearColor(.025f, .018f, .010f, .48f), 12.f,
            FLinearColor(.72f, .49f, .21f, .22f), 1.f);
        return &Brush;
    }

    const FEditableTextBoxStyle& EntryFieldStyle()
    {
        static const FEditableTextBoxStyle Style = FEditableTextBoxStyle(FCoreStyle::Get().GetWidgetStyle<FEditableTextBoxStyle>("NormalEditableTextBox"))
            .SetBackgroundImageNormal(FSlateRoundedBoxBrush(Ink, 2.f, FLinearColor(0.25f, 0.18f, 0.09f), 1.f))
            .SetBackgroundImageHovered(FSlateRoundedBoxBrush(Ink, 2.f, Muted, 1.f))
            .SetBackgroundImageFocused(FSlateRoundedBoxBrush(Ink, 2.f, Gold, 1.f))
            .SetBackgroundColor(FLinearColor::White).SetForegroundColor(Ivory).SetFocusedForegroundColor(Ivory)
            .SetReadOnlyForegroundColor(Muted).SetPadding(FMargin(12, 8));
        return Style;
    }

    const TMap<FString, TArray<FString>>& Roster()
    {
        static const TMap<FString, TArray<FString>> Values = {
            {TEXT("Empire"), {TEXT("Battle Prelate"), TEXT("Sunfire Templar"), TEXT("Ember Arcanist")}},
            {TEXT("Greenskin"), {TEXT("Warbrute")}}
        };
        return Values;
    }
}

void UWarFrontendWidget::InitializeArtwork()
{
    // Member brushes/styles and reflected material references survive Slate popup lifetimes and GC.
    Artwork.Reset();
    const auto Art = [this](const TCHAR* Name, FVector2D Size, FMargin Margin) {
        const FString Path = FString::Printf(TEXT("/Game/UI/Frontend/Artwork/M_%s.M_%s"), Name, Name);
        auto* Material = LoadObject<UMaterialInterface>(nullptr, *Path);
        auto* Instance = Material ? UMaterialInstanceDynamic::Create(Material, this) : nullptr;
        Artwork.Add(Instance);
        FSlateBrush Brush;
        Brush.SetResourceObject(Instance); Brush.ImageSize = Size;
        Brush.ImageType = ESlateBrushImageType::FullColor;
        Brush.DrawAs = Margin == FMargin(0) ? ESlateBrushDrawType::Image : ESlateBrushDrawType::Box;
        Brush.Margin = Margin;
        if (!Material) UE_LOG(LogTemp, Error, TEXT("Frontend artwork is missing: %s. Run import-frontend-artwork.py."), *Path);
        return Brush;
    };
    LogoBrush = Art(TEXT("Logo"), FVector2D(1666, 550), FMargin(0));
    WindowBrush = Art(TEXT("Window"), FVector2D(520, 812), FMargin(0));
    const FSlateBrush Button = Art(TEXT("Button"), FVector2D(460, 52), FMargin(.16f, .34f));
    FSlateBrush Hover = Button, Pressed = Button, Disabled = Button;
    Hover.TintColor = FLinearColor(1.3f, 1.18f, .9f);
    Pressed.TintColor = FLinearColor(.65f, .55f, .38f);
    Disabled.TintColor = FLinearColor(.35f, .31f, .24f);
    PrimaryButton = FButtonStyle().SetNormal(Button).SetHovered(Hover).SetPressed(Pressed).SetDisabled(Disabled)
        .SetNormalForeground(Ivory).SetHoveredForeground(FLinearColor::White).SetPressedForeground(Ivory)
        .SetDisabledForeground(Muted).SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0, 1, 0, 0));
    SecondaryButton = PrimaryButton;
    FSlateBrush Secondary = Button; Secondary.TintColor = FLinearColor(.78f, .72f, .60f);
    SecondaryButton.SetNormal(Secondary);
    const FSlateRoundedBoxBrush Selected(FLinearColor(.22f, .13f, .04f), 2.f);
    const FSlateRoundedBoxBrush SelectionHover(FLinearColor(.31f, .20f, .07f), 2.f);
    ChoiceRow = FCoreStyle::Get().GetWidgetStyle<FTableRowStyle>("TableView.Row");
    ChoiceRow.SetActiveBrush(Selected).SetInactiveBrush(Selected).SetActiveHoveredBrush(SelectionHover)
        .SetInactiveHoveredBrush(SelectionHover).SetEvenRowBackgroundHoveredBrush(SelectionHover)
        .SetOddRowBackgroundHoveredBrush(SelectionHover).SetSelectorFocusedBrush(SelectionHover)
        .SetTextColor(Ivory).SetSelectedTextColor(Ivory);
    ChoiceBox = FCoreStyle::Get().GetWidgetStyle<FComboBoxStyle>("ComboBox");
    auto ComboButton = ChoiceBox.ComboButtonStyle;
    auto Arrow = ComboButton.DownArrowImage; Arrow.TintColor = Ivory;
    ComboButton.SetDownArrowImage(Arrow).SetMenuBorderBrush(FSlateRoundedBoxBrush(Ink, 2.f, Gold, 1.f));
    ChoiceBox.SetComboButtonStyle(ComboButton);
    auto Empty = FSlateRoundedBoxBrush(Ink, 3.f, Gold, 1.f); Empty.ImageSize = FVector2D(18, 18);
    auto Checked = FSlateRoundedBoxBrush(Gold, 3.f, Ivory, 1.f); Checked.ImageSize = FVector2D(18, 18);
    MotionCheck = FCheckBoxStyle().SetUncheckedImage(Empty).SetUncheckedHoveredImage(Checked).SetUncheckedPressedImage(Checked)
        .SetCheckedImage(Checked).SetCheckedHoveredImage(Checked).SetCheckedPressedImage(Empty).SetPadding(FMargin(6, 0));
}

const FButtonStyle& UWarFrontendWidget::EntryButtonStyle(bool bPrimary) const
{ return bPrimary ? PrimaryButton : SecondaryButton; }

bool UWarFrontendWidget::ValidateCharacterName(const FString& Name, FString& Error)
{
    if (Name.Len() < 3 || Name.Len() > 24 || Name != Name.TrimStartAndEnd())
    { Error = TEXT("Use 3-24 letters, with optional spaces, apostrophes or hyphens."); return false; }
    int32 Letters = 0;
    for (TCHAR C : Name)
    {
        if (FChar::IsAlpha(C)) ++Letters;
        else if (C != TEXT(' ') && C != TEXT('\'') && C != TEXT('-'))
        { Error = TEXT("Names may contain letters, spaces, apostrophes and hyphens only."); return false; }
    }
    if (Letters < 3) { Error = TEXT("Your name needs at least three letters."); return false; }
    Error.Reset(); return true;
}

TSharedRef<SWidget> UWarFrontendWidget::RebuildWidget()
{
    SetIsFocusable(true);
    InitializeArtwork();
    if (!Presentation && GetGameInstance() && GetOwningPlayer())
        Presentation = NewObject<UWarFrontendPresentation>(GetGameInstance());
    if (Presentation) Presentation->Initialize();
    for (auto& Brush : CityBrushes) { Brush.ImageSize = FVector2D(1600, 900); Brush.DrawAs = ESlateBrushDrawType::NoDrawType; }
    CharacterBrush.ImageSize = FVector2D(800, 1000);
    CharacterBrush.DrawAs = ESlateBrushDrawType::Image;
    auto Root = SNew(SOverlay)
        + SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Ink)]
        + SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)
            [SNew(SImage).Image(&CityBrushes[0]).Visibility(EVisibility::HitTestInvisible)]]
        + SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)
            [SNew(SImage).Image(&CityBrushes[1]).Visibility(EVisibility::HitTestInvisible)
                .ColorAndOpacity_Lambda([this] { return FLinearColor(1, 1, 1, Presentation ? Presentation->GetBlend() : 0); })]]
        + SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
            .BorderBackgroundColor(FLinearColor(.018f, .010f, .004f, .38f)).Visibility(EVisibility::HitTestInvisible)]
        + SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
            [SNew(SBox).WidthOverride(1600).HeightOverride(900)
                [SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().AutoWidth().Padding(56, 44, 0, 44)
                    [SNew(SBox).WidthOverride(560)
                        [SNew(SOverlay)
                            + SOverlay::Slot()[SNew(SImage).Image(&WindowBrush).Visibility(EVisibility::HitTestInvisible)]
                            + SOverlay::Slot().Padding(FMargin(58, 96, 58, 42))
                            [SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Panel, SVerticalBox)]]]]
                    + SHorizontalBox::Slot().FillWidth(1).Padding(40, 44, 40, 20)
                    [SNew(SVerticalBox)
                        + SVerticalBox::Slot().FillHeight(1)
                        [SNew(SFrontendCharacter, Presentation.Get())
                            [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
                                [SNew(SBox).WidthOverride(800).HeightOverride(1000)
                                    .Visibility_Lambda([this] { return bHasDraft ? EVisibility::SelfHitTestInvisible : EVisibility::Hidden; })
                                    [SNew(SBorder).BorderImage(CharacterBackdrop()).Padding(0)
                                        [SNew(SImage).Image(&CharacterBrush)
                                            .Visibility_Lambda([this] { return Presentation && Presentation->HasCharacter() ? EVisibility::HitTestInvisible : EVisibility::Hidden; })]]]]]
                        + SVerticalBox::Slot().AutoHeight()
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(bHasDraft && Presentation ? Presentation->GetCharacterStatus() : FString()); })
                            .Justification(ETextJustify::Center).AutoWrapText(true).ColorAndOpacity(Ivory)]
                        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 8)
                        [SNew(SButton).ButtonStyle(&EntryButtonStyle(false)).ContentPadding(FMargin(48, 16))
                            .Visibility_Lambda([this] { return bHasDraft ? EVisibility::Visible : EVisibility::Collapsed; })
                            .OnClicked_Lambda([this] { if (Presentation) { if (Presentation->HasCharacter()) Presentation->ResetRotation(); else RefreshPreview(); } return FReply::Handled(); })
                            [SNew(STextBlock).ColorAndOpacity(Ivory).Text_Lambda([this] { return FText::FromString(Presentation && Presentation->HasCharacter() ? TEXT("RESET VIEW  /  DRAG TO ROTATE") : TEXT("Retry character preview")); })]]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 12)
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(Presentation ? Presentation->GetCityLabel() : FString()); })
                            .Font(FCoreStyle::GetDefaultFontStyle("Regular", 22)).ColorAndOpacity(Ivory).Justification(ETextJustify::Center)]
                        + SVerticalBox::Slot().AutoHeight()
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(Presentation ? Presentation->GetError() : FString()); }).AutoWrapText(true)
                            .ColorAndOpacity(Ivory).Justification(ETextJustify::Center)]
                        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
                        [SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().AutoWidth().Padding(8)
                            [SNew(SCheckBox).Style(&MotionCheck).IsChecked_Lambda([this] { return Presentation && Presentation->IsReducedMotion() ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
                                .OnCheckStateChanged_Lambda([this](ECheckBoxState State) { if (Presentation) Presentation->SetReducedMotion(State == ECheckBoxState::Checked); })
                                [SNew(STextBlock).Text(FText::FromString(TEXT("Reduced motion"))).ColorAndOpacity(Ivory)]]
                            + SHorizontalBox::Slot().AutoWidth().Padding(8)
                            [SNew(SButton).ButtonStyle(&EntryButtonStyle(false)).ContentPadding(FMargin(12, 6))
                                .Visibility_Lambda([this] { return Presentation && !Presentation->GetError().IsEmpty() ? EVisibility::Visible : EVisibility::Collapsed; })
                                .OnClicked_Lambda([this] { if (Presentation) Presentation->Retry(); return FReply::Handled(); })
                                [SNew(STextBlock).Text(FText::FromString(TEXT("Retry city views"))).ColorAndOpacity(Ivory)]]]]]]];
    ShowLogin();
    return Root;
}

void UWarFrontendWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if (Presentation) Presentation->Initialize();
}

void UWarFrontendWidget::NativeTick(const FGeometry& Geometry, float Delta)
{
    Super::NativeTick(Geometry, Delta);
    if (!Presentation) return;
    const auto Window = FSlateApplication::Get().FindWidgetWindow(TakeWidget());
    const bool bVisible = IsVisible() && Window.IsValid() && !Window->IsWindowMinimized();
    Presentation->Tick(Delta, bVisible);
    const int32 Active = Presentation->GetActiveCity();
    for (int32 Index = 0; Index < 2; ++Index)
    {
        auto* Texture = Presentation->GetCityTarget(Index == 0 ? Active : 1 - Active);
        CityBrushes[Index].SetResourceObject(Texture);
        CityBrushes[Index].DrawAs = Texture ? ESlateBrushDrawType::Image : ESlateBrushDrawType::NoDrawType;
    }
    CharacterBrush.SetResourceObject(Presentation->GetCharacterMaterial());
}

void UWarFrontendWidget::NativeDestruct()
{
    for (auto& Brush : CityBrushes) Brush.SetResourceObject(nullptr);
    CharacterBrush.SetResourceObject(nullptr);
    if (Presentation) Presentation->Shutdown();
    Super::NativeDestruct();
}

void UWarFrontendWidget::RefreshPreview()
{
    if (Presentation) Presentation->SelectCharacter(FName(*Race.ToLower().Replace(TEXT(" "), TEXT("_"))),
        FName(*Career.ToLower().Replace(TEXT(" "), TEXT("_"))), Body == TEXT("Male") ? FName("m") : FName("f"));
}

void UWarFrontendWidget::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    if (Presentation) Presentation->Shutdown();
    for (auto& Brush : CityBrushes) Brush.SetResourceObject(nullptr);
    CharacterBrush.SetResourceObject(nullptr);
    Panel.Reset(); Status.Reset();
}

void UWarFrontendWidget::AddHeading(const FString& Title, const FString& Subtitle, int32 Step)
{
    Panel->ClearChildren();
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
        [SNew(SBox).HeightOverride(88)
            [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
                [SNew(SImage).Image(&LogoBrush).Visibility(EVisibility::HitTestInvisible)]]];
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 14)
        [SNew(SBox).HeightOverride(1)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gold)]];
    auto Steps = SNew(SHorizontalBox);
    const TCHAR* Labels[] = {TEXT("01   SIGN IN"), TEXT("02   CREATE"), TEXT("03   EMBARK")};
    for (int32 Index = 0; Index < 3; ++Index)
        Steps->AddSlot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(Labels[Index]))
            .Font(FCoreStyle::GetDefaultFontStyle("Bold", 12)).ColorAndOpacity(Index == Step ? Gold : Muted)];
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 12)[Steps];
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
        [SNew(STextBlock).Text(FText::FromString(Title)).Font(FCoreStyle::GetDefaultFontStyle("Bold", 24)).ColorAndOpacity(Ivory)];
    if (Step != 1)
        Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 18)
            [SNew(STextBlock).Text(FText::FromString(Subtitle)).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14))
                .ColorAndOpacity(Muted).WrapTextAt(440)];
    Panel->AddSlot().AutoHeight()
        [SAssignNew(Status, STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).AutoWrapText(true)
            .ColorAndOpacity(FLinearColor(1.f, 0.52f, 0.29f)).Visibility(EVisibility::Collapsed)];
}

void UWarFrontendWidget::AddButton(const FString& Label, TFunction<void()> Action, bool bPrimary)
{
    Panel->AddSlot().AutoHeight().Padding(0, 4)
        [SNew(SButton).ButtonStyle(&EntryButtonStyle(bPrimary)).ContentPadding(FMargin(48, 10)).HAlign(HAlign_Center)
            .IsEnabled_Lambda([this]() {
                const auto* Controller = Cast<AWarPlayerController>(GetOwningPlayer());
                return !Controller || !Controller->IsCharacterEntryPending();
            })
            .OnClicked_Lambda([Action = MoveTemp(Action)]() { Action(); return FReply::Handled(); })
            [SNew(STextBlock).Text(FText::FromString(Label)).ColorAndOpacity(Ivory)
                .Font(FCoreStyle::GetDefaultFontStyle("Bold", 14))]];
}

void UWarFrontendWidget::ShowError(const FString& Error)
{
    if (Status) { Status->SetText(FText::FromString(Error)); Status->SetVisibility(Error.IsEmpty() ? EVisibility::Collapsed : EVisibility::Visible); }
}

void UWarFrontendWidget::ShowLogin()
{
    AddHeading(TEXT("Your realm awaits."), TEXT("Stand with the Accord. Rise with the Host.\nBegin your journey into a divided world."));
    Panel->AddSlot().AutoHeight().Padding(0, 6, 0, 14)
        [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.035f, 0.024f, 0.012f)).Padding(20)
            [SNew(STextBlock).Text(FText::FromString(TEXT("DEVELOPMENT PREVIEW\nSession character setup is available. Steam sign-in is not connected yet.")))
                .Font(FCoreStyle::GetDefaultFontStyle("Regular", 13)).ColorAndOpacity(Ivory).AutoWrapText(true)]];
#if !UE_BUILD_SHIPPING
    // Keep the usable local entry above optional account tools, including in short windows.
    if (GetWorld() && GetWorld()->GetNetMode() == NM_Standalone)
    {
        AddButton(TEXT("Local development login"), [this]() { ShowCreation(); });
    }
#endif
    AddButton(TEXT("Sign in with Steam"), [this]() {
        ShowError(TEXT("Steam account authentication is not connected yet. Online character storage and production entry remain unavailable."));
    }, false);
#if !UE_BUILD_SHIPPING
    AddButton(TEXT("Developer account"), [this]() { ShowDeveloperAccount(); }, false);
#endif
    AddButton(TEXT("Graphics"), [this] { UWarGraphicsWidget::Open(GetOwningPlayer(), this, true); }, false);
    AddButton(TEXT("Quit Game"), [this] {
        UKismetSystemLibrary::QuitGame(this, GetOwningPlayer(), EQuitPreference::Quit, false);
    }, false);
}

void UWarFrontendWidget::ShowDeveloperAccount()
{
#if !UE_BUILD_SHIPPING
    AddHeading(TEXT("Developer account"), TEXT("Optional GitHub account sign-in requires the development companion app. Shared server entry is still under development. For local character testing, return to login and choose Local development login."));
    AddButton(TEXT("Back to login"), [this]() { ShowLogin(); });
    AddButton(TEXT("Sign in with GitHub"), [this]() {
        if (auto* Account = GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>()) Account->BeginLogin();
    }, false);
    AddButton(TEXT("Sign out of developer account"), [this]() {
        if (auto* Account = GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>()) Account->Logout();
    }, false);
    Panel->AddSlot().AutoHeight().Padding(0, 8)[SNew(STextBlock).AutoWrapText(true).ColorAndOpacity(Muted)
        .Text_Lambda([this]() {
            const auto* Account = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>() : nullptr;
            return FText::FromString(Account ? Account->GetStatus() : TEXT("Development account unavailable."));
        })];
#endif
}

void UWarFrontendWidget::ShowCreation()
{
    bHasDraft = true;
    AddHeading(TEXT("Forge your legacy."), TEXT("Choose your character for this development session."), 1);
    Panel->AddSlot().AutoHeight().Padding(0, 6)[SNew(STextBlock).Text(FText::FromString(TEXT("CHARACTER NAME")))
        .Font(FCoreStyle::GetDefaultFontStyle("Bold", 12)).ColorAndOpacity(Gold)];
    Panel->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(SEditableTextBox).Style(&EntryFieldStyle()).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).HintText(FText::FromString(TEXT("Choose a name"))).Text(FText::FromString(CharacterName))
            .OnTextChanged_Lambda([this](const FText& Text) { CharacterName = Text.ToString(); })];
    // Each combo owns its options for the entire Slate lifetime, including menu popups.
    auto Combo = [this](const FString& Label, const TArray<FString>& Values, const FString& Selected, TFunction<void(FString)> Change) {
        auto Options = MakeShared<TArray<TSharedPtr<FString>>>();
        TSharedPtr<FString> Initial;
        for (const FString& Value : Values) { auto Item = MakeShared<FString>(Value); Options->Add(Item); if (Value == Selected) Initial = Item; }
        auto Current = MakeShared<TSharedPtr<FString>>(Initial);
        Panel->AddSlot().AutoHeight().Padding(0, 4, 0, 2)[SNew(STextBlock).Text(FText::FromString(Label.ToUpper())).Font(FCoreStyle::GetDefaultFontStyle("Bold", 12)).ColorAndOpacity(Gold)];
        Panel->AddSlot().AutoHeight().Padding(0, 4)
            [SNew(SComboBox<TSharedPtr<FString>>).ComboBoxStyle(&ChoiceBox).ItemStyle(&ChoiceRow).ButtonStyle(&EntryButtonStyle(false))
                .ContentPadding(FMargin(70, 12)).OptionsSource(&Options.Get()).InitiallySelectedItem(Initial)
                .OnGenerateWidget_Lambda([](TSharedPtr<FString> Item) -> TSharedRef<SWidget> {
                    return SNew(STextBlock).Text(FText::FromString(Item.IsValid() ? *Item : FString()))
                        .ColorAndOpacity(Ivory).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)); })
                .OnSelectionChanged_Lambda([Options, Current, Change](TSharedPtr<FString> Item, ESelectInfo::Type) { if (Item) { *Current = Item; Change(*Item); } })
                [SNew(STextBlock).Text_Lambda([Current] { return FText::FromString(Current->IsValid() ? **Current : FString()); })
                    .ColorAndOpacity(Ivory).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14))]];
    };
    if (!Roster().Contains(Race)) Race = TEXT("Empire");
    if (!Roster()[Race].Contains(Career)) Career = Roster()[Race][0];
    Body = TEXT("Male");
    Combo(TEXT("Race"), {TEXT("Empire"), TEXT("Greenskin")}, Race,
        [this](FString Value) { if (Race != Value) { Race = Value; Career = Roster()[Race][0]; ShowCreation(); } });
    Combo(TEXT("Career"), Roster()[Race], Career, [this](FString Value) { Career = Value; RefreshPreview(); });
    Combo(TEXT("Body"), {TEXT("Male")}, Body, [this](FString Value) { Body = Value; RefreshPreview(); });
    RefreshPreview();
    AddButton(TEXT("Review character"), [this]() {
        CharacterName = CharacterName.TrimStartAndEnd();
        FString Error;
        if (!ValidateCharacterName(CharacterName, Error)) { ShowError(Error); return; }
        ShowSelection();
    });
    AddButton(TEXT("Graphics"), [this] { UWarGraphicsWidget::Open(GetOwningPlayer(), this, true); }, false);
    AddButton(TEXT("Back to login"), [this]() { ShowLogin(); }, false);
}

void UWarFrontendWidget::ShowSelection()
{
    const bool bAegis = Race == TEXT("Empire") || Race == TEXT("Dwarf") || Race == TEXT("High Elf");
    AddHeading(TEXT("Your character"), FString::Printf(TEXT("%s\n%s  /  %s  /  %s\n%s\nStarting city: %s\n\nSession-only development draft."),
        *CharacterName, *Race, *Career, *Body, bAegis ? TEXT("Aegis Accord") : TEXT("Riftbound Host"),
        bAegis ? TEXT("Bastion of Aegis") : TEXT("Riftspire Citadel")), 2);
    AddButton(TEXT("Enter campaign"), [this]() {
        if (auto* Controller = Cast<AWarPlayerController>(GetOwningPlayer()))
        {
            FString RaceId = Race.ToLower().Replace(TEXT(" "), TEXT("_"));
            FString ClassId = Career.ToLower().Replace(TEXT(" "), TEXT("_"));
            Controller->ServerCreateDevelopmentCharacter(CharacterName, FName(*RaceId), FName(*ClassId), Body == TEXT("Male") ? FName("m") : FName("f"));
        }
    });
    AddButton(TEXT("Edit character"), [this]() { ShowCreation(); }, false);
    AddButton(TEXT("Graphics"), [this] { UWarGraphicsWidget::Open(GetOwningPlayer(), this, true); }, false);
    AddButton(TEXT("Back to login"), [this]() { ShowLogin(); }, false);
}
