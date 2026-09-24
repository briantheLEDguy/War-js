#include "WarInterfacePages.h"
#include "WarInterfaceStyle.h"
#include "WarInterfaceCatalog.h"
#include "WarContentSubsystem.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "Engine/GameInstance.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Input/SSpinBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

namespace
{
    class SWarGmTools : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SWarGmTools) {} SLATE_END_ARGS()
        void Construct(const FArguments&, AWarPlayerController* Controller)
        {
            Owner=Controller;
            const auto* State=Controller->GetPlayerState<AWarPlayerState>();
            SelectedLevel=State ? FMath::Clamp(State->GetInventory().CharacterProgression.Level,1,WarProgression::MaxGmLevel) : 1;
            const auto* Content=Controller->GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
            Catalog=FWarInterfaceCatalog::Parse(Content ? Content->GetInterfaceCatalogSource() : nullptr);
            auto Root=SNew(SVerticalBox);
            ChildSlot[Root];
            Root->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(STextBlock).AutoWrapText(true).ColorAndOpacity(WarInterfaceStyle::Gold)
                .Text(FText::FromString(Controller->CanUseGmTools() ? TEXT("GM development session. Changes remain subject to server validation.")
                    : TEXT("Enter a character in the local development workbench to use GM controls. Standalone play requires Enable local development GM in project settings or -WarDevelopmentGM. Networked sessions do not grant GM access.")))];
            Root->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(STextBlock).AutoWrapText(true).ColorAndOpacity(WarInterfaceStyle::Text)
                .Font(FCoreStyle::GetDefaultFontStyle("Regular",14)).Text_Lambda([this] {
                    return Owner.IsValid() ? FText::FromString(Owner->GetWorldEditMessage()) : FText::GetEmpty(); })];
            const auto Command=[this](const FString& Label,TFunction<void(AWarPlayerController*)> Action) -> TSharedRef<SWidget> {
                return SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(FMargin(10,9))
                    .IsEnabled_Lambda([this] { return Owner.IsValid() && Owner->CanUseGmTools(); })
                    .OnClicked_Lambda([this,Action] { if (Owner.IsValid()) Action(Owner.Get()); return FReply::Handled(); })
                    [SNew(STextBlock).Text(FText::FromString(Label)).Font(FCoreStyle::GetDefaultFontStyle("Regular",14)).ColorAndOpacity(WarInterfaceStyle::Text)];
            };
            auto Utilities=SNew(SHorizontalBox);
            Utilities->AddSlot().FillWidth(1).Padding(2)[Command(TEXT("Restore"),[](auto* PC) { PC->ServerGmRestore(); })];
            Utilities->AddSlot().FillWidth(1).Padding(2)[Command(TEXT("Reset cooldowns"),[](auto* PC) { PC->ServerGmResetCooldowns(); })];
            Utilities->AddSlot().FillWidth(1).Padding(2)[Command(TEXT("Copy coordinates"),[](auto* PC) { PC->CopyGmCoordinates(); })];
            Utilities->AddSlot().FillWidth(1).Padding(2)[Command(TEXT("Return to spawn"),[](auto* PC) { PC->ServerReturnToDevelopmentSpawn(); })];
            Root->AddSlot().AutoHeight()[Utilities];
            Root->AddSlot().AutoHeight().Padding(0,12,0,4)[SNew(STextBlock).ColorAndOpacity(WarInterfaceStyle::Gold)
                .Text_Lambda([this] {
                    const auto* PlayerState=Owner.IsValid() ? Owner->GetPlayerState<AWarPlayerState>() : nullptr;
                    return FText::FromString(FString::Printf(TEXT("Your level: %d | Set level (1-%d)"),
                        PlayerState ? PlayerState->GetInventory().CharacterProgression.Level : 1,WarProgression::MaxGmLevel)); })];
            Root->AddSlot().AutoHeight()[SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1)[SNew(SSpinBox<int32>).MinValue(1).MaxValue(WarProgression::MaxGmLevel)
                    .MinSliderValue(1).MaxSliderValue(WarProgression::MaxGmLevel).Delta(1)
                    .IsEnabled_Lambda([this] { return Owner.IsValid() && Owner->CanUseGmTools(); })
                    .Value_Lambda([this] { return SelectedLevel; })
                    .OnValueChanged_Lambda([this](int32 Value) { SelectedLevel=Value; })]
                + SHorizontalBox::Slot().AutoWidth().Padding(8,0)[Command(TEXT("Set level"),[this](auto* PC) { PC->ServerGmSetLevel(SelectedLevel); })]];
            Root->AddSlot().AutoHeight().Padding(0,4,0,8)[SNew(STextBlock).AutoWrapText(true).ColorAndOpacity(WarInterfaceStyle::Text)
                .Text(FText::FromString(TEXT("Updates stats and ability unlocks, resets XP, and restores health and mana for this session.")))];
            Root->AddSlot().AutoHeight().Padding(0,10)[SNew(STextBlock).Text(FText::FromString(TEXT("Go to character (exact name, current world)"))).ColorAndOpacity(WarInterfaceStyle::Gold)];
            Root->AddSlot().AutoHeight()[SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1)[SNew(SEditableTextBox).HintText(FText::FromString(TEXT("Character name")))
                    .OnTextChanged_Lambda([this](const FText& Text) { TargetName=Text.ToString().Left(32); })]
                + SHorizontalBox::Slot().AutoWidth().Padding(8,0)[Command(TEXT("Go"),[this](auto* PC) { PC->ServerGmGoToCharacter(TargetName); })]];
            Root->AddSlot().AutoHeight().Padding(0,12)[SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth()[Command(TEXT("Fly / walk"),[](auto* PC) {
                    if (auto* Character=Cast<AWarCharacter>(PC->GetPawn())) PC->ServerSetDevelopmentTraversal(!Character->IsDevelopmentFlying(),Character->GetDevelopmentSpeed()); })]
                + SHorizontalBox::Slot().FillWidth(1).Padding(16,0)[SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).ColorAndOpacity(WarInterfaceStyle::Text).Text_Lambda([this] {
                        const auto* Character=Owner.IsValid() ? Cast<AWarCharacter>(Owner->GetPawn()) : nullptr;
                        return FText::FromString(Character ? FString::Printf(TEXT("Speed %.2fx | %s | %s down / %s up"),Character->GetDevelopmentSpeed(),Character->IsDevelopmentFlying() ? TEXT("Flying") : TEXT("Walking"),*Owner->GetControlKey(TEXT("FlyDown")).GetDisplayName().ToString(),*Owner->GetControlKey(TEXT("Interact")).GetDisplayName().ToString()) : TEXT("Character unavailable")); })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0,8)[SNew(SSlider).MinValue(0.25f).MaxValue(6.f).StepSize(0.25f)
                        .IsEnabled_Lambda([this] { return Owner.IsValid() && Owner->CanUseGmTools(); })
                        .Value_Lambda([this] { const auto* Character=Owner.IsValid() ? Cast<AWarCharacter>(Owner->GetPawn()) : nullptr; return Character ? Character->GetDevelopmentSpeed() : 1.f; })
                        .OnValueChanged_Lambda([this](float Value) { if (Owner.IsValid()) if (const auto* Character=Cast<AWarCharacter>(Owner->GetPawn())) Owner->ServerSetDevelopmentTraversal(Character->IsDevelopmentFlying(),Value); })]]];
            Root->AddSlot().AutoHeight().Padding(0,8)[Command(TEXT("Toggle performance stats"),[](auto* PC) { PC->ConsoleCommand(TEXT("stat fps"),true); })];
            Root->AddSlot().AutoHeight().Padding(0,8)[Command(TEXT("Open world builder"),[](auto* PC) { PC->ToggleWorldEditor(); })];
            Root->AddSlot().AutoHeight().Padding(0,8)[Command(TEXT("Open Ability Workshop"),[](auto* PC) { PC->OpenAbilityWorkshop(); })];
            Root->AddSlot().AutoHeight().Padding(0,10)[SNew(STextBlock).ColorAndOpacity(WarInterfaceStyle::Gold).Text(FText::FromString(TEXT("Zone teleport - loaded destinations only")))];
            Root->AddSlot().AutoHeight()[SNew(SSearchBox).HintText(FText::FromString(TEXT("Find a campaign zone")))
                .OnTextChanged_Lambda([this](const FText& Text) { ZoneQuery=Text.ToString(); RefreshZones(); })];
            Root->AddSlot().AutoHeight().Padding(0,8)[SNew(SBox).HeightOverride(190)[SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(ZoneRows,SVerticalBox)]]];
            RefreshZones();
        }
    private:
        TWeakObjectPtr<AWarPlayerController> Owner;
        FWarInterfaceCatalog Catalog;
        FString TargetName,ZoneQuery;
        int32 SelectedLevel=1;
        TSharedPtr<SVerticalBox> ZoneRows;
        void RefreshZones()
        {
            if (!ZoneRows) return;
            ZoneRows->ClearChildren();
            for (const auto& Zone : Catalog.Zones)
            {
                if (!(Zone.Name+TEXT(" ")+Zone.Id).Contains(ZoneQuery)) continue;
                ZoneRows->AddSlot().AutoHeight().Padding(0,0,0,5)[SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(8)
                    .IsEnabled_Lambda([this] { return Owner.IsValid() && Owner->CanUseGmTools(); })
                    .OnClicked_Lambda([this,Id=FName(*Zone.Id)] { if (Owner.IsValid()) Owner->ServerGmTeleportZone(Id); return FReply::Handled(); })
                    [SNew(STextBlock).Text(FText::FromString(Zone.Name+TEXT("  /  ")+Zone.Tier)).ColorAndOpacity(WarInterfaceStyle::Text)]];
            }
        }
    };
}
TSharedRef<SWidget> WarBuildGmTools(AWarPlayerController* Controller) { return SNew(SWarGmTools,Controller); }
