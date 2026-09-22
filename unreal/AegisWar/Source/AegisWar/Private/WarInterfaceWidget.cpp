#include "WarInterfaceWidget.h"
#include "WarAbilityCatalog.h"
#include "WarCharacter.h"
#include "WarGraphicsWidget.h"
#include "WarMenuFrame.h"
#include "WarInterfaceRules.h"
#include "WarControlSettings.h"
#include "WarInterfaceStyle.h"
#include "WarInterfacePages.h"
#include "Kismet/GameplayStatics.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCityNpc.h"
#include "WarQuestNpc.h"
#include "WarCraftingStation.h"
#include "WarResourceNode.h"
#include "WarContentSubsystem.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/GameUserSettings.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Text/STextBlock.h"
#include "Rendering/DrawElements.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/CoreStyle.h"

void UWarInterfaceWidget::ShowPage(FName Page) { PendingBinding=NAME_None; CurrentPage = Page; if (Body) Refresh(); }

TSharedRef<SWidget> UWarInterfaceWidget::RebuildWidget()
{
    SetIsFocusable(true);
    namespace Theme = WarInterfaceStyle;
    auto NavigationColumn = SNew(SVerticalBox);
    NavigationColumn->AddSlot().AutoHeight().Padding(8, 10, 8, 4)
        [SNew(STextBlock).Text(FText::FromString(TEXT("A E G I S"))).ColorAndOpacity(Theme::Gold).Font(FCoreStyle::GetDefaultFontStyle("Bold", 23))];
    NavigationColumn->AddSlot().AutoHeight().Padding(8, 0, 8, 26)
        [SNew(STextBlock).Text(FText::FromString(TEXT("W A R"))).ColorAndOpacity(Theme::Text).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16))];
    NavigationColumn->AddSlot().AutoHeight().Padding(8, 0, 8, 14)
        [SNew(STextBlock).Text(FText::FromString(TEXT("FIELD COMMAND"))).ColorAndOpacity(Theme::Muted).Font(FCoreStyle::GetDefaultFontStyle("Bold", 10))];
    int32 Chapter = 0;
    for (const FName Page : {FName(TEXT("Menu")), FName(TEXT("Map")), FName(TEXT("Campaign")), FName(TEXT("Character")), FName(TEXT("Abilities")), FName(TEXT("Options")), FName(TEXT("Guide")), FName(TEXT("GM Tools"))})
    {
        const FString Number = FString::Printf(TEXT("%02d"), ++Chapter);
        NavigationColumn->AddSlot().AutoHeight().Padding(0, 0, 0, 8)
            [SNew(SButton).ButtonStyle(&Theme::Button()).HAlign(HAlign_Fill).ContentPadding(FMargin(12, 13))
                .OnClicked_Lambda([this, Page] { ShowPage(Page); return FReply::Handled(); })
                [SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 12, 0)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 11)).Text(FText::FromString(Number)).ColorAndOpacity(Theme::Gold)]
                    + SHorizontalBox::Slot().FillWidth(1)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 15)).Text(FText::FromName(Page))
                            .ColorAndOpacity_Lambda([this, Page] { return CurrentPage == Page ? WarInterfaceStyle::Gold : WarInterfaceStyle::Text; })]
                    + SHorizontalBox::Slot().AutoWidth()
                        [SNew(STextBlock).Text_Lambda([this, Page] { return FText::FromString(CurrentPage == Page ? TEXT("<") : TEXT("")); }).ColorAndOpacity(Theme::Gold)]]];
    }
    NavigationColumn->AddSlot().FillHeight(1)[SNew(SBox)];
    NavigationColumn->AddSlot().AutoHeight().Padding(4, 10, 4, 12)
        [SNew(STextBlock).Text(FText::FromString(TEXT("The realm does not rest."))).ColorAndOpacity(Theme::Muted).Font(FCoreStyle::GetDefaultFontStyle("Italic", 10))];
    NavigationColumn->AddSlot().AutoHeight()[SNew(SButton).ButtonStyle(&Theme::PrimaryButton()).ContentPadding(FMargin(12, 14)).HAlign(HAlign_Center)
        .OnClicked_Lambda([this] {
            if (auto* PC = Cast<AWarPlayerController>(GetOwningPlayer())) PC->CloseInterface();
            return FReply::Handled();
        })[SNew(STextBlock).Text(FText::FromString(TEXT("RESUME   [Esc]"))).Font(FCoreStyle::GetDefaultFontStyle("Bold", 13)).ColorAndOpacity(Theme::Sidebar)]];
    auto Panel = SNew(SWarMenuFrame)
        [SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth()
                [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.01f,0.012f,0.015f,0.55f)).Padding(20)
                    [SNew(SBox).WidthOverride(174)[NavigationColumn]]]
            + SHorizontalBox::Slot().AutoWidth()
                [SNew(SBox).WidthOverride(1)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Theme::Line)]]
            + SHorizontalBox::Slot().FillWidth(1).Padding(32, 28)
                [SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Body, SVerticalBox)]]];
    auto Root = SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.001f, 0.002f, 0.004f, 0.8f)).Padding(18)
        [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
            [SNew(SBox).WidthOverride(1160).HeightOverride(840)[Panel]]];
    Refresh();
    return Root;
}

void UWarInterfaceWidget::ReleaseSlateResources(bool Children)
{
    Super::ReleaseSlateResources(Children);
    Body.Reset();
}

FReply UWarInterfaceWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    auto* PC = Cast<AWarPlayerController>(GetOwningPlayer());
    if (PC && !Event.IsRepeat())
    {
        const FKey Key = Event.GetKey();
        if (!PendingBinding.IsNone())
        {
            if (Key == EKeys::Escape) BindingMessage=TEXT("Binding cancelled.");
            else if (PC->SetControlKey(PendingBinding,Key,BindingMessage)) BindingMessage=TEXT("Binding saved.");
            PendingBinding=NAME_None; Refresh(); return FReply::Handled();
        }
        if (Key == EKeys::Escape) { PC->CloseInterface(); return FReply::Handled(); }

    }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}

FReply UWarInterfaceWidget::NativeOnPreviewMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event)
{
    if (!PendingBinding.IsNone())
    {
        if (auto* PC=Cast<AWarPlayerController>(GetOwningPlayer()))
            if (PC->SetControlKey(PendingBinding,Event.GetEffectingButton(),BindingMessage)) BindingMessage=TEXT("Binding saved.");
        PendingBinding=NAME_None; Refresh(); return FReply::Handled();
    }
    return Super::NativeOnPreviewMouseButtonDown(Geometry,Event);
}

void UWarInterfaceWidget::AddText(const FString& Text, int32 Size)
{
    Body->AddSlot().AutoHeight().Padding(0, 0, 0, 14)
        [SNew(STextBlock).Text(FText::FromString(Text)).ColorAndOpacity(Size > 20 ? WarInterfaceStyle::Text : WarInterfaceStyle::Muted).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle(Size > 20 ? "Bold" : "Regular", Size))];
}
void UWarInterfaceWidget::AddButton(const FString& Text, TFunction<void()> Action)
{
    Body->AddSlot().AutoHeight().Padding(0, 0, 0, 10)
        [SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).HAlign(HAlign_Fill).ContentPadding(FMargin(16, 12)).OnClicked_Lambda([Action] { Action(); return FReply::Handled(); })
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).ColorAndOpacity(WarInterfaceStyle::Text).Text(FText::FromString(Text))]
                + SHorizontalBox::Slot().AutoWidth().Padding(12, 0)[SNew(STextBlock).Text(FText::FromString(TEXT(">"))).ColorAndOpacity(WarInterfaceStyle::Gold)]]];
}

void UWarInterfaceWidget::Refresh()
{
    if (!Body) return;
    Body->ClearChildren();
    auto* PC = Cast<AWarPlayerController>(GetOwningPlayer());
    if (!PC) return;
    Body->AddSlot().AutoHeight().Padding(0, 0, 0, 10)
        [SNew(STextBlock).Text(FText::FromString(TEXT("A E G I S   /   F I E L D   J O U R N A L")))
            .Font(FCoreStyle::GetDefaultFontStyle("Bold", 10)).ColorAndOpacity(WarInterfaceStyle::Gold)];
    AddText(CurrentPage == TEXT("Menu") ? TEXT("War Council") : CurrentPage == TEXT("Map") ? TEXT("Local Map") : CurrentPage.ToString(), 32);
    Body->AddSlot().AutoHeight().Padding(0, 0, 0, 18)[SNew(SBox).HeightOverride(1)
        [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(WarInterfaceStyle::Line)]];
    const auto KeyLabel=[PC](const TCHAR* Action) { return PC->GetControlKey(FName(Action)).GetDisplayName().ToString(); };
    if (CurrentPage == TEXT("Menu"))
    {
        AddText(TEXT("Prepare your next move. Your session remains live."));
        AddButton(TEXT("Inventory, equipment & crafting [")+KeyLabel(TEXT("Inventory"))+TEXT("]"), [PC] { PC->ToggleInventory(); });
        AddButton(TEXT("Quest journal [")+KeyLabel(TEXT("Quests"))+TEXT("]"), [PC] { PC->ToggleQuestLog(); });
        AddButton(TEXT("Local map [")+KeyLabel(TEXT("Map"))+TEXT("]"), [this] { ShowPage(TEXT("Map")); });
        AddButton(TEXT("Character [")+KeyLabel(TEXT("Character"))+TEXT("]"), [this] { ShowPage(TEXT("Character")); });
        AddButton(TEXT("Options"), [this] { ShowPage(TEXT("Options")); });
        AddButton(TEXT("UI Settings & action bars"), [this] { ShowPage(TEXT("UI Settings")); });
        AddButton(TEXT("Clean Map"), [this] { ShowPage(TEXT("Clean Map")); });
        AddButton(TEXT("Campaign map"), [this] { ShowPage(TEXT("Campaign")); });
        AddButton(TEXT("How-to guide [")+KeyLabel(TEXT("Guide"))+TEXT(" / F1]"), [this] { ShowPage(TEXT("Guide")); });
        AddButton(TEXT("GM Tools [")+KeyLabel(TEXT("GM"))+TEXT("]"), [this] { ShowPage(TEXT("GM Tools")); });
        AddButton(TEXT("Exit to Login..."), [this] { ShowPage(TEXT("Exit to Login")); });
        AddButton(TEXT("Quit game..."), [this] { ShowPage(TEXT("Quit")); });
    }
    else if (CurrentPage == TEXT("Quit"))
    {
        AddText(TEXT("Leave this session and close the game? Save any GM draft before leaving."));
        AddButton(TEXT("Quit game"), [PC] { UKismetSystemLibrary::QuitGame(PC, PC, EQuitPreference::Quit, false); });
        AddButton(TEXT("Keep playing"), [this] { ShowPage(TEXT("Menu")); });
    }
    else if (CurrentPage == TEXT("Map") || CurrentPage == TEXT("Clean Map") || CurrentPage == TEXT("Campaign") || CurrentPage == TEXT("Atlas"))
    {
        Body->AddSlot().AutoHeight()[WarBuildAtlas(PC,CurrentPage == TEXT("Campaign") || CurrentPage == TEXT("Atlas"),CurrentPage == TEXT("Clean Map"))];
    }
    else if (CurrentPage == TEXT("GM Tools"))
    {
        Body->AddSlot().AutoHeight()[WarBuildGmTools(PC)];
    }
    else if (CurrentPage == TEXT("Character"))
    {
        Body->AddSlot().AutoHeight()[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular", 20)).Text_Lambda([Weak = TWeakObjectPtr<AWarPlayerController>(PC)] {
            const auto* State = Weak.IsValid() ? Weak->GetPlayerState<AWarPlayerState>() : nullptr;
            if (!State) return FText::FromString(TEXT("Waiting for character state..."));
            const auto& Progress = State->GetInventory().CharacterProgression;
            const auto* Stats = State->GetAttributes();
            return FText::FromString(FString::Printf(TEXT("%s\n\n%s\n\nLevel %d\nXP %lld / %lld\nGold %lld\nStrength %lld\n\nHealth %.0f / %.0f\nMana %.0f / %.0f"),
                *State->GetPlayerName(), State->GetRealm() == EWarRealm::Aegis ? TEXT("Aegis Accord") : State->GetRealm() == EWarRealm::Riftbound ? TEXT("Riftbound Host") : TEXT("Realm pending"),
                Progress.Level, Progress.Xp, WarProgression::XpForLevel(Progress.Level), Progress.Gold, State->GetEffectiveStrength(),
                Stats ? Stats->GetHealth() : 0, Stats ? Stats->GetMaxHealth() : 0, Stats ? Stats->GetMana() : 0, Stats ? Stats->GetMaxMana() : 0));
        })];
        AddButton(TEXT("Manage equipment"), [PC] { PC->ToggleInventory(); });
    }
    else if (CurrentPage == TEXT("Options"))
    {
        AddButton(TEXT("UI Settings & Edit UI"), [this] { ShowPage(TEXT("UI Settings")); });
        AddButton(TEXT("Keyboard & mouse bindings"), [this] { ShowPage(TEXT("Key bindings")); });
        AddButton(TEXT("Graphics"), [this, PC] { UWarGraphicsWidget::Open(PC, this, false); });
        AddText(TEXT("Camera and audio preferences save immediately."));
        const auto Slider = [this](const FString& Label, TAttribute<float> Value, TFunction<void(float)> Change) {
            AddText(Label);
            Body->AddSlot().AutoHeight().Padding(0, 0, 0, 18)[SNew(SSlider).SliderBarColor(WarInterfaceStyle::Line).SliderHandleColor(WarInterfaceStyle::Gold).Value(Value).OnValueChanged_Lambda([Change](float V) { Change(V); })];
        };
        Slider(TEXT("Look sensitivity (0.25 - 3.0)"), TAttribute<float>::CreateLambda([PC] { return (PC->GetLocalCameraState().LookSensitivity - 0.25) / 2.75; }),
            [PC](float V) { auto& C = PC->GetLocalCameraState(); C.SetPreferences(0.25 + V * 2.75, C.ZoomSensitivity, C.bInvertX, C.bInvertY); PC->SaveInterfacePreferences(); });
        Slider(TEXT("Zoom sensitivity (0.25 - 3.0)"), TAttribute<float>::CreateLambda([PC] { return (PC->GetLocalCameraState().ZoomSensitivity - 0.25) / 2.75; }),
            [PC](float V) { auto& C = PC->GetLocalCameraState(); C.SetPreferences(C.LookSensitivity, 0.25 + V * 2.75, C.bInvertX, C.bInvertY); PC->SaveInterfacePreferences(); });
        for (bool X : {true, false}) Body->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
            [SNew(SCheckBox).IsChecked_Lambda([PC, X] { const auto& C = PC->GetLocalCameraState(); return (X ? C.bInvertX : C.bInvertY) ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
                .OnCheckStateChanged_Lambda([PC, X](ECheckBoxState State) { auto& C = PC->GetLocalCameraState(); if (X) C.bInvertX = State == ECheckBoxState::Checked; else C.bInvertY = State == ECheckBoxState::Checked; PC->SaveInterfacePreferences(); })
                [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).Text(FText::FromString(X ? TEXT("Invert horizontal camera") : TEXT("Invert vertical camera")))]];
        Slider(TEXT("Master volume"), TAttribute<float>::CreateLambda([PC] { return PC->GetInterfaceVolume(); }),
            [PC](float V) { PC->SetInterfaceVolume(V); PC->SaveInterfacePreferences(); });
        AddButton(TEXT("Reset camera"), [PC] { PC->GetLocalCameraState().SetPreferences(1, 1, false, false); PC->SaveInterfacePreferences(); });
    }
    else if (CurrentPage == TEXT("UI Settings"))
    {
        AddText(TEXT("Create as many bars as you need, with 1-10 buttons each. Positions, actions and individual keys save on this computer. New bars start empty and unbound."));
        AddButton(TEXT("Edit UI - drag bars into position"), [PC] { PC->SetEditingUi(true); });
        AddButton(TEXT("Add a bar..."), [this] { ShowPage(TEXT("Add bar")); });
        AddButton(TEXT("Keyboard & mouse bindings"), [this] { ShowPage(TEXT("Key bindings")); });
        AddText(TEXT("Assign any class ability below. Locked abilities show their unlock level on the bar; your full kit unlocks through level 8. Summons marked unavailable cannot be activated."));
        AddText(BindingMessage);
        for (const auto& Bar : PC->GetActionBars())
        {
            AddText(FString::Printf(TEXT("Bar %d  |  %d buttons"), Bar.Id + 1, Bar.Buttons), 22);
            AddButton(TEXT("Change button count"), [this, Id = Bar.Id] { EditingBarId = Id; ShowPage(TEXT("Resize bar")); });
            for (int32 Button = 0; Button < Bar.Buttons; ++Button)
            {
                const int32 SlotIndex = Bar.Slot(Button);
                const FKey Key = PC->GetControlKey(WarActionBar::Binding(SlotIndex));
                AddButton(FString::Printf(TEXT("Button %d: %s   [%s]"), Button + 1, *PC->GetActionLabel(PC->GetActionSlot(SlotIndex)),
                    Key.IsValid() ? *Key.GetDisplayName().ToString() : TEXT("Unbound")),
                    [this, SlotIndex] { EditingActionSlot = SlotIndex; ShowPage(TEXT("Configure button")); });
            }
            AddButton(TEXT("Remove this bar..."), [this, Id = Bar.Id] { EditingBarId = Id; ShowPage(TEXT("Remove bar")); });
        }
    }
    else if (CurrentPage == TEXT("Add bar") || CurrentPage == TEXT("Resize bar"))
    {
        AddText(TEXT("Choose the number of buttons. Resizing preserves assignments so they return when you expand the bar again."));
        for (int32 Count = 1; Count <= 10; ++Count)
            AddButton(FString::Printf(TEXT("%d buttons"), Count), [this, PC, Count] {
                if (CurrentPage == TEXT("Add bar")) PC->AddActionBar(Count);
                else PC->ResizeActionBar(EditingBarId, Count);
                ShowPage(TEXT("UI Settings"));
            });
        AddButton(TEXT("Back"), [this] { ShowPage(TEXT("UI Settings")); });
    }
    else if (CurrentPage == TEXT("Remove bar"))
    {
        AddText(TEXT("Remove this bar and release its key bindings? Other bars stay unchanged."));
        AddButton(TEXT("Remove bar"), [this, PC] { PC->RemoveActionBar(EditingBarId); ShowPage(TEXT("UI Settings")); });
        AddButton(TEXT("Cancel"), [this] { ShowPage(TEXT("UI Settings")); });
    }
    else if (CurrentPage == TEXT("Abilities"))
    {
        AddText(TEXT("Your class abilities"), 24);
        AddText(TEXT("Three starter abilities are available at level 1. The remaining abilities unlock through level 8. Assign abilities to any bar in UI Settings."));
        AddText(PC->GetClassAbilityStatus());
        const auto* LocalPawn = Cast<AWarCharacter>(PC->GetPawn());
        const auto* AbilityCatalog = PC->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
        const auto* PlayerState = PC->GetPlayerState<AWarPlayerState>();
        if (LocalPawn && AbilityCatalog && PlayerState) for (const auto* Ability : AbilityCatalog->Kit(LocalPawn->GetCareerId()))
        {
            AddText(Ability->Name + FString::Printf(TEXT("  |  Level %d"), Ability->UnlockLevel), 20);
            AddText(Ability->Summary);
            AddText(FString::Printf(TEXT("%.0f mana  |  %.1f s cooldown  |  %.1f m range"), Ability->Mana, Ability->Cooldown, Ability->Range / 100));
            if (!Ability->UnavailableReason.IsEmpty()) AddText(Ability->UnavailableReason);
            else if (PlayerState->GetInventory().CharacterProgression.Level < Ability->UnlockLevel) AddText(TEXT("Locked until the required level."));
            if (PC->HasActionSlot(Ability->Slot)) AddButton(FString::Printf(TEXT("Assign to first bar, button %d"), Ability->Slot + 1),
                [PC, Id = Ability->Id, Button = Ability->Slot] { PC->SetActionSlot(Button, Id); });
        }
        AddButton(TEXT("Configure action bars"), [this] { ShowPage(TEXT("UI Settings")); });
    }
    else if (CurrentPage == TEXT("Configure button"))
    {
        AddText(PC->GetActionLabel(PC->GetActionSlot(EditingActionSlot)), 22);
        AddText(BindingMessage);
        for (FName Action : PC->GetAvailableActions())
            AddButton(TEXT("Assign: ") + PC->GetActionLabel(Action), [this, PC, Action] { PC->SetActionSlot(EditingActionSlot, Action); Refresh(); });
        const FName Binding = WarActionBar::Binding(EditingActionSlot);
        const FKey Key = PC->GetControlKey(Binding);
        AddButton(TEXT("Set key [") + (Key.IsValid() ? Key.GetDisplayName().ToString() : TEXT("Unbound")) + TEXT("]"), [this, Binding] {
            PendingBinding = Binding; BindingMessage = TEXT("Press a keyboard or mouse button; Escape cancels."); Refresh();
        });
        AddButton(TEXT("Clear key binding"), [this, PC, Binding] { PC->SetControlKey(Binding, EKeys::Invalid, BindingMessage); BindingMessage = TEXT("Key cleared."); Refresh(); });
        AddButton(TEXT("Back to UI Settings"), [this] { ShowPage(TEXT("UI Settings")); });
    }
    else if (CurrentPage == TEXT("Key bindings"))
    {
        AddText(TEXT("Select an action, then press a key. Escape cancels selection; F1 always opens the guide. Wheel zoom remains fixed. Changes save immediately."));
        AddText(BindingMessage);
        for (const auto& Entry : WarControls::Defaults()) if (!WarActionBar::IsSlotBinding(Entry.Action))
            AddButton(Entry.Label+TEXT("   [")+PC->GetControlKey(Entry.Action).GetDisplayName().ToString()+TEXT("]"), [this,Action=Entry.Action] {
                PendingBinding=Action; BindingMessage=TEXT("Press a key for ")+Action.ToString()+TEXT(" (Escape cancels)..."); Refresh();
            });
        AddButton(TEXT("Configure individual bar buttons and their keys"), [this] { ShowPage(TEXT("UI Settings")); });
        AddButton(TEXT("Reset all bindings"), [this,PC] { PC->ResetControlKeys(); PendingBinding=NAME_None; BindingMessage=TEXT("Defaults restored."); Refresh(); });
        AddButton(TEXT("Back to options"), [this] { ShowPage(TEXT("Options")); });
    }
    else if (CurrentPage == TEXT("Guide"))
    {
        Body->AddSlot().AutoHeight()[WarBuildGuide(PC)];
    }
    else if (CurrentPage == TEXT("Exit to Login"))
    {
        AddText(TEXT("Leave this session and return to character entry? Current native development characters and progression are session-only. Save your GM draft before leaving."));
        AddButton(TEXT("Return to login"), [PC] {
            if (PC->GetWorld()->GetNetMode() == NM_Standalone)
                UGameplayStatics::OpenLevel(PC,FName(*UWorld::RemovePIEPrefix(PC->GetWorld()->GetOutermost()->GetName())));
            else PC->ClientReturnToMainMenuWithTextReason(FText::FromString(TEXT("You left the session.")));
        });
        AddButton(TEXT("Keep playing"), [this] { ShowPage(TEXT("Menu")); });
    }
}
