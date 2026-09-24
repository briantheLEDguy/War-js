#include "WarFrontendWidget.h"
#include "WarDevelopmentAccount.h"
#include "Engine/GameInstance.h"
#include "Kismet/KismetSystemLibrary.h"
#include "WarGraphicsWidget.h"
#include "WarMenuFrame.h"
#include "WarPlayerController.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/STextComboBox.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Widgets/Layout/SScaleBox.h"

namespace
{
    const FLinearColor Gold(0.72f, 0.49f, 0.21f);
    const FLinearColor Ivory(0.91f, 0.86f, 0.74f);
    const FLinearColor Muted(0.46f, 0.51f, 0.56f);
    const FLinearColor Ink(0.012f, 0.019f, 0.027f);

    // Slate stores style pointers; these must outlive every screen and popup.
    const FButtonStyle& EntryButtonStyle(bool bPrimary)
    {
        static const FButtonStyle Primary = FButtonStyle()
            .SetNormal(FSlateRoundedBoxBrush(Gold, 2.f))
            .SetHovered(FSlateRoundedBoxBrush(FLinearColor(0.92f, 0.69f, 0.34f), 2.f))
            .SetPressed(FSlateRoundedBoxBrush(FLinearColor(0.5f, 0.31f, 0.11f), 2.f))
            .SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0, 1, 0, 0));
        static const FButtonStyle Secondary = FButtonStyle()
            .SetNormal(FSlateRoundedBoxBrush(FLinearColor(0.026f, 0.039f, 0.052f), 2.f, FLinearColor(0.15f, 0.18f, 0.2f), 1.f))
            .SetHovered(FSlateRoundedBoxBrush(FLinearColor(0.055f, 0.073f, 0.087f), 2.f, Gold, 1.f))
            .SetPressed(FSlateRoundedBoxBrush(Ink, 2.f, Gold, 1.f))
            .SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0, 1, 0, 0));
        return bPrimary ? Primary : Secondary;
    }

    const FEditableTextBoxStyle& EntryFieldStyle()
    {
        static const FEditableTextBoxStyle Style = FEditableTextBoxStyle(FCoreStyle::Get().GetWidgetStyle<FEditableTextBoxStyle>("NormalEditableTextBox"))
            .SetBackgroundImageNormal(FSlateRoundedBoxBrush(Ink, 2.f, FLinearColor(0.14f, 0.18f, 0.21f), 1.f))
            .SetBackgroundImageHovered(FSlateRoundedBoxBrush(Ink, 2.f, Muted, 1.f))
            .SetBackgroundImageFocused(FSlateRoundedBoxBrush(Ink, 2.f, Gold, 1.f))
            .SetForegroundColor(Ivory).SetFocusedForegroundColor(Ivory).SetPadding(FMargin(16, 12));
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
    auto Root = SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.004f, 0.008f, 0.014f, 0.96f))
        .HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(28)
        [SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly)
            [SNew(SBox).WidthOverride(820).HeightOverride(940)
                [SNew(SWarMenuFrame)
                    [SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Panel, SVerticalBox)]]]]];
    ShowLogin();
    return Root;
}

void UWarFrontendWidget::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    Panel.Reset(); Status.Reset();
}

void UWarFrontendWidget::AddHeading(const FString& Title, const FString& Subtitle, int32 Step)
{
    Panel->ClearChildren();
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 18)
        [SNew(STextBlock).Text(FText::FromString(TEXT("T W O   R E A L M S   /   O N E   W A R")))
            .Justification(ETextJustify::Center).Font(FCoreStyle::GetDefaultFontStyle("Regular", 12)).ColorAndOpacity(Gold)];
    Panel->AddSlot().AutoHeight()
        [SNew(STextBlock).Text(FText::FromString(TEXT("AEGIS WAR"))).Justification(ETextJustify::Center)
            .Font(FCoreStyle::GetDefaultFontStyle("Bold", 54)).ColorAndOpacity(Ivory)];
    Panel->AddSlot().AutoHeight().Padding(0, 10, 0, 26)
        [SNew(STextBlock).Text(FText::FromString(TEXT("AEGIS ACCORD     /     RIFTBOUND HOST"))).Justification(ETextJustify::Center)
            .Font(FCoreStyle::GetDefaultFontStyle("Regular", 12)).ColorAndOpacity(Muted)];
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 24)
        [SNew(SBox).HeightOverride(1)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gold)]];
    auto Steps = SNew(SHorizontalBox);
    const TCHAR* Labels[] = {TEXT("01   SIGN IN"), TEXT("02   CREATE"), TEXT("03   EMBARK")};
    for (int32 Index = 0; Index < 3; ++Index)
        Steps->AddSlot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(Labels[Index]))
            .Font(FCoreStyle::GetDefaultFontStyle("Bold", 12)).ColorAndOpacity(Index == Step ? Gold : Muted)];
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 26)[Steps];
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
        [SNew(STextBlock).Text(FText::FromString(Title)).Font(FCoreStyle::GetDefaultFontStyle("Bold", 27)).ColorAndOpacity(Ivory)];
    Panel->AddSlot().AutoHeight().Padding(0, 0, 0, 18)
        [SNew(STextBlock).Text(FText::FromString(Subtitle)).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16))
            .ColorAndOpacity(Muted).AutoWrapText(true)];
    Panel->AddSlot().AutoHeight()
        [SAssignNew(Status, STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).AutoWrapText(true)
            .ColorAndOpacity(FLinearColor(1.f, 0.52f, 0.29f)).Visibility(EVisibility::Collapsed)];
}

void UWarFrontendWidget::AddButton(const FString& Label, TFunction<void()> Action, bool bPrimary)
{
    Panel->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(SButton).ButtonStyle(&EntryButtonStyle(bPrimary)).ContentPadding(FMargin(22, 15)).HAlign(HAlign_Center)
            .IsEnabled_Lambda([this]() {
                const auto* Controller = Cast<AWarPlayerController>(GetOwningPlayer());
                return !Controller || !Controller->IsCharacterEntryPending();
            })
            .OnClicked_Lambda([Action = MoveTemp(Action)]() { Action(); return FReply::Handled(); })
            [SNew(STextBlock).Text(FText::FromString(Label)).ColorAndOpacity(bPrimary ? Ink : Ivory)
                .Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))]];
}

void UWarFrontendWidget::ShowError(const FString& Error)
{
    if (Status) { Status->SetText(FText::FromString(Error)); Status->SetVisibility(Error.IsEmpty() ? EVisibility::Collapsed : EVisibility::Visible); }
}

void UWarFrontendWidget::ShowLogin()
{
    AddHeading(TEXT("Your realm awaits."), TEXT("Stand with the Accord. Rise with the Host.\nBegin your journey into a divided world."));
    Panel->AddSlot().AutoHeight().Padding(0, 6, 0, 24)
        [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.028f, 0.042f, 0.054f)).Padding(20)
            [SNew(STextBlock).Text(FText::FromString(TEXT("DEVELOPMENT PREVIEW\nSteam sign-in is not connected yet. Character setup is available for this session.")))
                .Font(FCoreStyle::GetDefaultFontStyle("Regular", 15)).ColorAndOpacity(Ivory).AutoWrapText(true)]];
#if !UE_BUILD_SHIPPING
    // Keep the usable local entry above optional account tools, including in short windows.
    if (GetWorld() && GetWorld()->GetNetMode() == NM_Standalone)
    {
        AddButton(TEXT("Local development login"), [this]() { ShowCreation(); });
        Panel->AddSlot().AutoHeight().Padding(0, 4, 0, 8)[SNew(STextBlock).AutoWrapText(true).ColorAndOpacity(Ivory)
            .Text(FText::FromString(TEXT("Create a character for this test session. No account or companion app required.")))];
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
    AddHeading(TEXT("Forge your legacy."), TEXT("Choose your race, career and body. This development character lasts for this session; entry requires an available native model."), 1);
    Panel->AddSlot().AutoHeight().Padding(0, 6)[SNew(STextBlock).Text(FText::FromString(TEXT("CHARACTER NAME")))
        .Font(FCoreStyle::GetDefaultFontStyle("Bold", 12)).ColorAndOpacity(Gold)];
    Panel->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(SEditableTextBox).Style(&EntryFieldStyle()).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).HintText(FText::FromString(TEXT("Choose a name"))).Text(FText::FromString(CharacterName))
            .OnTextChanged_Lambda([this](const FText& Text) { CharacterName = Text.ToString(); })];
    // Each combo owns its options for the entire Slate lifetime, including menu popups.
    auto Combo = [this](const FString& Label, const TArray<FString>& Values, const FString& Selected, TFunction<void(FString)> Change) {
        auto Options = MakeShared<TArray<TSharedPtr<FString>>>();
        TSharedPtr<FString> Initial;
        for (const FString& Value : Values) { auto Item = MakeShared<FString>(Value); Options->Add(Item); if (Value == Selected) Initial = Item; }
        Panel->AddSlot().AutoHeight().Padding(0, 10, 0, 4)[SNew(STextBlock).Text(FText::FromString(Label.ToUpper())).Font(FCoreStyle::GetDefaultFontStyle("Bold", 12)).ColorAndOpacity(Gold)];
        Panel->AddSlot().AutoHeight().Padding(0, 4)
            [SNew(STextComboBox).ButtonStyle(&EntryButtonStyle(false)).ColorAndOpacity(Ivory).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).ContentPadding(FMargin(16, 10)).OptionsSource(&Options.Get()).InitiallySelectedItem(Initial)
                .OnSelectionChanged_Lambda([Options, Change](TSharedPtr<FString> Item, ESelectInfo::Type) { if (Item) Change(*Item); })];
    };
    if (!Roster().Contains(Race)) Race = TEXT("Empire");
    if (!Roster()[Race].Contains(Career)) Career = Roster()[Race][0];
    Body = TEXT("Male");
    Combo(TEXT("Race"), {TEXT("Empire"), TEXT("Greenskin")}, Race,
        [this](FString Value) { if (Race != Value) { Race = Value; Career = Roster()[Race][0]; ShowCreation(); } });
    Combo(TEXT("Career"), Roster()[Race], Career, [this](FString Value) { Career = Value; });
    Combo(TEXT("Body"), {TEXT("Male")}, Body, [this](FString Value) { Body = Value; });
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
    AddHeading(TEXT("Your character"), FString::Printf(TEXT("%s\n%s  /  %s  /  %s\n%s\nStarting city: %s\n\nSession-only development draft. A 3D character preview is not yet available."),
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
