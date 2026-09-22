#include "WarInterfacePages.h"
#include "WarInterfaceCatalog.h"
#include "WarInterfaceStyle.h"
#include "WarContentSubsystem.h"
#include "WarPlayerController.h"
#include "Engine/GameInstance.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

namespace
{
    class SWarGuide : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SWarGuide) {} SLATE_END_ARGS()
        void Construct(const FArguments&, AWarPlayerController* Controller)
        {
            const auto* Content = Controller->GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
            Catalog = FWarInterfaceCatalog::Parse(Content ? Content->GetInterfaceCatalogSource() : nullptr);
            const auto Native = [](const TCHAR* Id, const TCHAR* Title, const TCHAR* Text) {
                FWarGuidePage Page{Id,TEXT("native_howto"),Title,TEXT("native"),Text,{}};
                Page.SearchText = (Page.Title + TEXT(" ") + Page.Text).ToLower(); return Page;
            };
            Catalog.Sections.Insert({TEXT("native_howto"),TEXT("How to play")}, 0);
            Catalog.Pages.Insert(Native(TEXT("native-start"), TEXT("Getting started"),
                TEXT("Create your character from the entry menu, then enter the realm.\n\nW A S D moves, Space jumps, and Num Lock toggles auto-run. Hold the right mouse button to orbit the camera; scroll to zoom.\n\nApproach a named NPC or station and press E. Use I for inventory, L for quests, C for character details, M for the map and H or F1 for this guide. Esc closes the active panel or opens the War Council.\n\nPanels block movement and combat input; the world continues running. The Options page changes camera, audio and graphics preferences.")), 0);
            Catalog.Pages.Insert(Native(TEXT("native-maps"), TEXT("Reading the maps"),
                TEXT("Map opens the current zone. Clean Map hides all optional markers so buildings and roads remain readable. Toggle individual layers to show people, quest NPCs, resources, crafting, exits and objectives.\n\nDrag with the left mouse button to pan. Scroll to zoom around the pointer. Fit resets the view. Current returns to your loaded location.\n\nCampaign shows the full 32-zone graph. Click a zone to inspect its route, then click again to inspect the zone. Right-click steps back to Route or Campaign. Blue is Aegis, red is Riftbound; these are homeland affiliations, not live ownership.\n\nCurrent-zone geometry and markers use loaded native actors. Other zones show the authored map reference, not proof that their terrain, population or travel is playable.")), 1);
            Catalog.Pages.Insert(Native(TEXT("native-quests"), TEXT("Quests and city services"),
                TEXT("Quest NPCs display an exclamation mark for available work and a question mark for turn-in. Approach and press E to read the offer, accept or complete it. L opens your journal and the HUD tracks up to three active quests.\n\nMerchants expose their available goods through E. Inventory space, gold and distance are checked before each transaction. Class and profession teachers provide reference guidance. Banking and unimplemented services are identified in their panels.\n\nI opens equipment, consumables, portable recipes and cultivation. Approach a crafting station and press E for station recipes. Resource nodes can be gathered with E when available.")), 2);
            Catalog.Pages.Insert(Native(TEXT("native-gm"), TEXT("Using GM tools"),
                TEXT("Open GM Tools from the War Council. GM controls are enabled by default after entering a character in local editor Play or standalone development play. Standalone access can be disabled with Enable local development GM in project settings; -WarDevelopmentGM remains an explicit opt-in. They do not grant online privileges.\n\nUse Restore for native health/mana, Reset Cooldowns for implemented abilities, Copy Coordinates for your native location, or Zone Spawn to return to the arrival. Flight uses Q down and E up; speed ranges from 0.25x to 6x.\n\nGo To Character requires an exact unique character name in the current world. Zone Teleport lists the whole campaign but only accepts a loaded, validated landing destination.\n\nBuild opens the native world editor: select a placed model, adjust its transform, duplicate it, snap or drop it to a surface, hide/restore, undo/redo, and save/load a draft. Reset restores the authored baseline as an undoable change.\n\nThe original browser terrain brushes, generic collider authoring and shared publication are separate migration work; the native editor does not fabricate those operations.")), 3);
            Catalog.Pages.Insert(Native(TEXT("native-action-bars"), TEXT("Action bars and Edit UI"),
                TEXT("Open Escape > UI Settings to add bars with 1-10 buttons. Configure each button's action and keyboard or mouse binding. Additional bars start empty and unbound. You can create as many bars as you need.\n\nChoose Edit UI and drag the gold handles. Done or Escape saves positions and returns to settings. Shrinking a bar preserves hidden assignments and keys; removing a bar releases its keys.\n\nThe initial bar uses 1-0. Tab cycles nearby visible hostiles; V toggles the action cursor for clicking buttons and reading tooltips. These keys can be changed in Options. Basic strike requires melee range, mana and a clear path. Its cooldown comes from live combat state. Potion buttons use matching items in your bag and require a missing resource.\n\nYour initial bar contains the ten class abilities. Three starter abilities unlock at level 1; the rest unlock through level 8. Escape > Abilities lists the kit, costs and unlocks. Class resources, cooldowns, damage, healing, buffs, control and movement effects are server-authoritative. Three source-unimplemented summons remain marked unavailable. Basic strike and potions can be assigned to additional bars.")), 4);
            auto Tabs = SNew(SHorizontalBox);
            for (const auto& Section : Catalog.Sections)
                Tabs->AddSlot().FillWidth(1).Padding(2)[SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(6)
                    .OnClicked_Lambda([this, Id = Section.Key] { ActiveSection = Id; ActivePage = INDEX_NONE; Refresh(); return FReply::Handled(); })
                    [SNew(STextBlock).Text(FText::FromString(Section.Value)).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",11))
                        .ColorAndOpacity_Lambda([this, Id=Section.Key] { return ActiveSection == Id ? WarInterfaceStyle::Gold : WarInterfaceStyle::Text; })]];
            ChildSlot[SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)
                    [SNew(SSearchBox).HintText(FText::FromString(TEXT("Search this section (choose All to search the whole guide)")))
                        .OnTextChanged_Lambda([this](const FText& Text) { Query = Text.ToString(); ActivePage = INDEX_NONE; Refresh(); })]
                + SVerticalBox::Slot().AutoHeight()[Tabs]
                + SVerticalBox::Slot().AutoHeight().Padding(0,8)
                    [SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).Text(FText::FromString(TEXT("All sections")))
                        .OnClicked_Lambda([this] { ActiveSection.Empty(); ActivePage = INDEX_NONE; Refresh(); return FReply::Handled(); })]
                + SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(400)
                    [SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(0.32f).Padding(0,0,16,0)[SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(PageList,SVerticalBox)]]
                        + SHorizontalBox::Slot().FillWidth(0.68f)[SAssignNew(ArticleScroll,SScrollBox)+SScrollBox::Slot()[SAssignNew(Article,SVerticalBox)]]]]];
            Refresh();
        }
    private:
        FWarInterfaceCatalog Catalog;
        FString ActiveSection = TEXT("native_howto"), Query;
        int32 ActivePage = INDEX_NONE;
        TSharedPtr<SVerticalBox> PageList, Article;
        TSharedPtr<SScrollBox> ArticleScroll;
        void Refresh()
        {
            PageList->ClearChildren();
            const auto Matches = Catalog.SearchGuide(ActiveSection,Query);
            if (!Matches.Contains(ActivePage)) ActivePage = Matches.IsEmpty() ? INDEX_NONE : Matches[0];
            PageList->AddSlot().AutoHeight().Padding(0,0,0,8)[SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%d pages"),Matches.Num()))).ColorAndOpacity(WarInterfaceStyle::Muted)];
            for (int32 Index : Matches)
                PageList->AddSlot().AutoHeight().Padding(0,0,0,5)[SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(8)
                    .OnClicked_Lambda([this,Index] { ActivePage=Index; Refresh(); return FReply::Handled(); })
                    [SNew(STextBlock).Text(FText::FromString(Catalog.Pages[Index].Title)).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",13))
                        .ColorAndOpacity(ActivePage == Index ? WarInterfaceStyle::Gold : WarInterfaceStyle::Text)]];
            Article->ClearChildren(); ArticleScroll->ScrollToStart();
            if (!Catalog.Pages.IsValidIndex(ActivePage))
            { Article->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("No guide pages match. Clear the search or choose another section."))).AutoWrapText(true)]; return; }
            const auto& Page = Catalog.Pages[ActivePage];
            Article->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(STextBlock).Text(FText::FromString(Page.Title)).Font(FCoreStyle::GetDefaultFontStyle("Bold",21)).AutoWrapText(true).ColorAndOpacity(WarInterfaceStyle::Text)];
            if (Page.Status != TEXT("native")) Article->AddSlot().AutoHeight().Padding(0,0,0,12)
                [SNew(STextBlock).AutoWrapText(true).ColorAndOpacity(WarInterfaceStyle::Gold).Text(FText::FromString(
                    TEXT("Original game reference. Source status: ") + Page.Status + TEXT(". This describes the browser baseline; consult How to play for current native controls and availability.")))];
            Article->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Page.Text)).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",15)).ColorAndOpacity(WarInterfaceStyle::Muted)];
        }
    };
}
TSharedRef<SWidget> WarBuildGuide(AWarPlayerController* Controller) { return SNew(SWarGuide,Controller); }
