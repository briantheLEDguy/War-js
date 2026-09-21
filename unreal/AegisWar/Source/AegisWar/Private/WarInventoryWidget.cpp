#include "WarInventoryWidget.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

TSharedRef<SWidget> UWarInventoryWidget::RebuildWidget()
{
    DisplayedRevision = INDEX_NONE;
    return SNew(SBox).WidthOverride(540.f).HeightOverride(650.f)
        [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).Padding(16.f).BorderBackgroundColor(FLinearColor(0.025f, 0.03f, 0.045f, 1.f))
            [SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [SNew(SSearchBox).InitialText(FText::FromString(Search)).HintText(NSLOCTEXT("AegisWar", "SearchInventory", "Search inventory"))
                    .OnTextChanged_Lambda([this](const FText& Text) {
                        Search = Text.ToString();
                        if (auto* State = GetOwningPlayerState<AWarPlayerState>()) Refresh(State);
                    })]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [SNew(SButton).Text_Lambda([this] {
                    return bSortByName ? NSLOCTEXT("AegisWar", "InventoryNameOrder", "Order: name")
                        : NSLOCTEXT("AegisWar", "InventorySlotOrder", "Order: bag slot");
                }).OnClicked_Lambda([this] {
                    bSortByName = !bSortByName;
                    if (auto* State = GetOwningPlayerState<AWarPlayerState>()) Refresh(State);
                    return FReply::Handled();
                })]
                + SVerticalBox::Slot().FillHeight(1.f)
                [SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Rows, SVerticalBox)]]]];
}

void UWarInventoryWidget::NativeTick(const FGeometry& Geometry, const float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    auto* State = GetOwningPlayerState<AWarPlayerState>();
    if (Rows && State && (DisplayedState != State || DisplayedRevision != State->GetInventory().Revision)) Refresh(State);
}

void UWarInventoryWidget::ReleaseSlateResources(const bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    Rows.Reset();
    DisplayedState.Reset();
}

void UWarInventoryWidget::Refresh(AWarPlayerState* State)
{
    if (!Rows || !State) return;
    DisplayedState = State;
    const auto& Inventory = State->GetInventory();
    DisplayedRevision = Inventory.Revision;
    Rows->ClearChildren();
    Rows->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 26)).Text(FText::FromString(FString::Printf(TEXT("Inventory — %d / 24 slots"), Inventory.Items.Num())))];
    Rows->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
        [SNew(SButton)
            .OnClicked_Lambda([WeakThis = TWeakObjectPtr<UWarInventoryWidget>(this)] {
                if (WeakThis.IsValid())
                    if (auto* Controller = Cast<AWarPlayerController>(WeakThis->GetOwningPlayer())) Controller->ToggleInventory();
                return FReply::Handled();
            })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 20)).Text(NSLOCTEXT("AegisWar", "CloseInventory", "Close inventory"))]];
    auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    Rows->AddSlot().AutoHeight().Padding(0, 0, 0, 8)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true).Text_Lambda([WeakState = TWeakObjectPtr<AWarPlayerState>(State)] {
            return WeakState.IsValid() ? WeakState->GetInventoryMessage() : FText::GetEmpty();
        })];
    TArray<FWarInventoryItem> DisplayItems = Inventory.Items;
    DisplayItems.Sort([Content, this](const auto& Left, const auto& Right) {
        if (bSortByName)
        {
            const FString LeftName = Content ? Content->GetItemDisplayName(Left.Key).ToString() : Left.Key.ToString();
            const FString RightName = Content ? Content->GetItemDisplayName(Right.Key).ToString() : Right.Key.ToString();
            const int32 Order = LeftName.Compare(RightName, ESearchCase::IgnoreCase);
            if (Order != 0) return Order < 0;
        }
        return Left.Slot < Right.Slot;
    });
    for (const auto& DisplayItem : DisplayItems)
    {
        const auto* Item = &DisplayItem;
        const int32 BagSlot = Item->Slot;
        const bool bEquipped = Inventory.Equipment.ContainsByPredicate([BagSlot](const auto& Row) { return Row.BagSlot == BagSlot; });
        const FString Name = Content ? Content->GetItemDisplayName(Item->Key).ToString() : Item->Key.ToString();
        if (!Search.IsEmpty() && !Name.Contains(Search) && !Item->Kind.ToString().Contains(Search)
            && !Item->EquipSlot.ToString().Contains(Search)) continue;
        FString Label = FString::Printf(TEXT("%02d  %s ×%d%s"), BagSlot + 1, *Name, Item->Quantity, bEquipped ? TEXT("  [Equipped]") : TEXT(""));
        if (Item->bHasAffix) Label += FString::Printf(TEXT("  Strength %+d"), Item->StrengthBonus);
        float Health, Mana;
        const bool bConsumable = Content && Content->GetConsumableEffect(Item->Key, Health, Mana);
        if (bConsumable) Label += TEXT("  [Use]");
        Rows->AddSlot().AutoHeight().Padding(0, 3)
            [SNew(SButton).IsEnabled(!Item->EquipSlot.IsNone() || bConsumable)
                .OnClicked_Lambda([WeakState = TWeakObjectPtr<AWarPlayerState>(State), Revision = DisplayedRevision, BagSlot, bEquipped, bConsumable] {
                    if (WeakState.IsValid())
                    {
                        if (bConsumable) WeakState->ServerUseConsumable(Revision, BagSlot);
                        else WeakState->ServerChangeEquipment(Revision, BagSlot, !bEquipped);
                    }
                    return FReply::Handled();
                })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 20)).AutoWrapText(true).Text(FText::FromString(Label))]];
    }
    Rows->AddSlot().AutoHeight().Padding(0, 12)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true).Text(FText::FromString(FString::Printf(
            TEXT("Click equipment to equip or unequip.\n%d reward entries await bag space."), Inventory.PendingRewards.Num())))];
    if (!Content) return;
    Rows->AddSlot().AutoHeight().Padding(0, 12)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 22)).Text(NSLOCTEXT("AegisWar", "PortableCrafting", "Portable crafting"))];
    for (const auto RecipeId : Content->GetCraftRecipeIds())
    {
        FWarCraftRecipe Recipe; FString Error;
        if (!Content->GetCraftRecipe(RecipeId, Recipe, Error)) continue;
        const auto* Progress = Inventory.Professions.FindByPredicate([&Recipe](const auto& Row) { return Row.Profession == Recipe.Profession; });
        const int32 Xp = Progress ? Progress->Xp : 0;
        const FString Label = FString::Printf(TEXT("Craft %s\nRank %d required · current rank %d · %d XP"),
            *Recipe.Name, Recipe.MinimumRank, WarCrafting::RankForXp(Xp), Xp);
        Rows->AddSlot().AutoHeight().Padding(0, 3)
            [SNew(SButton).OnClicked_Lambda([WeakState = TWeakObjectPtr<AWarPlayerState>(State), RecipeId, Revision = DisplayedRevision] {
                if (WeakState.IsValid()) WeakState->ServerCraftRecipe(RecipeId, Revision, nullptr);
                return FReply::Handled();
            })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true).Text(FText::FromString(Label))]];
    }
}
