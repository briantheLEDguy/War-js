#include "WarCityServiceWidget.h"
#include "WarUiArtwork.h"
#include "WarCityNpc.h"
#include "WarCityServices.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

void UWarCityServiceWidget::SetNpc(AWarCityNpc* Value) { Npc = Value; Revision = INDEX_NONE; Refresh(); }
TSharedRef<SWidget> UWarCityServiceWidget::RebuildWidget()
{
    return SNew(SBox).WidthOverride(620).HeightOverride(650)
        [SNew(SWarArtWindow)
            [SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(Rows,SVerticalBox)]]];
}
void UWarCityServiceWidget::ReleaseSlateResources(bool ReleaseChildren)
{ Super::ReleaseSlateResources(ReleaseChildren); Rows.Reset(); Revision = INDEX_NONE; }
void UWarCityServiceWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);
    auto* Controller=Cast<AWarPlayerController>(GetOwningPlayer());
    if (!Npc.IsValid() || !Controller || !Npc->CanInteract(Controller->GetPawn()))
    { if (Controller) Controller->CloseCityService(); return; }
    const auto* State=GetOwningPlayerState<AWarPlayerState>();
    if (State && State->GetInventory().Revision!=Revision) Refresh();
}
void UWarCityServiceWidget::Refresh()
{
    auto* State=GetOwningPlayerState<AWarPlayerState>();
    auto* Content=GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    if (!Rows || !Npc.IsValid() || !State || !Content) return;
    Revision=State->GetInventory().Revision;
    Rows->ClearChildren();
    const auto Label=[this](const FString& Text) {
        Rows->AddSlot().AutoHeight().Padding(0,0,0,12)
            [SNew(STextBlock).AutoWrapText(true).ColorAndOpacity(FLinearColor(.88f,.85f,.76f))
                .Font(FCoreStyle::GetDefaultFontStyle("Regular",18)).Text(FText::FromString(Text))];
    };
    Label(Npc->DisplayName);
    Rows->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(SButton).Text(FText::FromString(TEXT("Close")))
        .OnClicked_Lambda([this] { if (auto* Controller=Cast<AWarPlayerController>(GetOwningPlayer())) Controller->CloseCityService(); return FReply::Handled(); })];
    Rows->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(STextBlock).AutoWrapText(true).Text_Lambda([Weak=TWeakObjectPtr<AWarPlayerState>(State)] {
        return Weak.IsValid() ? Weak->GetInventoryMessage() : FText::GetEmpty(); })];
    auto Offers=WarCityServices::Offers(Npc->GetService());
    if (Offers.IsEmpty()) { Label(Content->GetCityTeachingText(Npc->GetService())); return; }
    Label(FString::Printf(TEXT("Gold: %lld — buy or sell one item per click"),State->GetInventory().CharacterProgression.Gold));
    TArray<FName> Keys; Offers.GetKeys(Keys); Keys.Sort(FNameLexicalLess());
    const auto Button=[this,State](const FString& Text,FName Key,bool Sell,int32 BagSlot) {
        const int32 Displayed=Revision;
        Rows->AddSlot().AutoHeight().Padding(0,0,0,8)[SNew(SButton).Text(FText::FromString(Text))
            .OnClicked_Lambda([WeakState=TWeakObjectPtr<AWarPlayerState>(State),WeakNpc=Npc,Key,Sell,BagSlot,Displayed] {
                if (WeakState.IsValid() && WeakNpc.IsValid()) WeakState->ServerTradeWithCityNpc(WeakNpc.Get(),FGuid::NewGuid(),Key,Sell,1,BagSlot,Displayed);
                return FReply::Handled(); })];
    };
    for (const auto Key:Keys)
    {
        const FString Name=Content->GetItemDisplayName(Key).ToString();
        Button(FString::Printf(TEXT("Buy %s — %d gold"),*Name,Offers[Key]),Key,false,INDEX_NONE);
        for (const auto& Item:State->GetInventory().Items)
            if (Item.Key==Key && !State->GetInventory().Equipment.ContainsByPredicate([&Item](const auto& Ref){return Ref.BagSlot==Item.Slot;}))
                Button(FString::Printf(TEXT("Sell %s — %d gold (stack %d)"),*Name,Offers[Key]/2,Item.Quantity),Key,true,Item.Slot);
    }
}
