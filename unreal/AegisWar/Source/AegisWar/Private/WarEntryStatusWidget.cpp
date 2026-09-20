#include "WarEntryStatusWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/TextBlock.h"

TSharedRef<SWidget> UWarEntryStatusWidget::RebuildWidget()
{
    if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("WidgetTree"));
    if (Message && WidgetTree->RootWidget) return Super::RebuildWidget();
    UBorder* Panel = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("EntryPanel"));
    Panel->SetPadding(FMargin(48.f));
    Panel->SetBrushColor(FLinearColor(0.025f, 0.03f, 0.04f, 0.98f));
    Panel->SetVerticalAlignment(VAlign_Center);
    Panel->SetHorizontalAlignment(HAlign_Center);
    Message = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("EntryMessage"));
    Message->SetColorAndOpacity(FSlateColor(FLinearColor::White));
    Message->SetAutoWrapText(true);
    Message->SetWrapTextAt(760.f);
    Panel->SetContent(Message);
    WidgetTree->RootWidget = Panel;
    SetEntryError(EntryError);
    return Super::RebuildWidget();
}

void UWarEntryStatusWidget::SetEntryError(const FText& Error)
{
    EntryError = Error;
    if (Message) Message->SetText(FText::Format(NSLOCTEXT("AegisWar", "EntryUnavailable", "Aegis War — entry unavailable\n\n{0}\n\nNo character has been spawned."), EntryError));
}
