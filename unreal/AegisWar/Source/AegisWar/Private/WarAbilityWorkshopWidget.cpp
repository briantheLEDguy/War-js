#include "WarAbilityWorkshopWidget.h"
#include "SWarAbilityWorkshop.h"
#include "WarPlayerController.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Widgets/Layout/SDPIScaler.h"

TSharedRef<SWidget> UWarAbilityWorkshopWidget::RebuildWidget()
{
    // The spreadsheet uses readable fixed dimensions and collapses panels; the game's
    // resolution-dependent HUD scale must not shrink its text or hide the breakpoint.
    return SNew(SDPIScaler).DPIScale_Lambda([this] { return 1.f/FMath::Max(.1f,UWidgetLayoutLibrary::GetViewportScale(this)); })
        [SAssignNew(Workshop,SWarAbilityWorkshop,Cast<AWarPlayerController>(GetOwningPlayer()))];
}
void UWarAbilityWorkshopWidget::ReleaseSlateResources(bool bReleaseChildren)
{ Super::ReleaseSlateResources(bReleaseChildren); Workshop.Reset(); }
bool UWarAbilityWorkshopWidget::VerifyInteractions(FString& Error)
{ return Workshop && Workshop->VerifyInteractions(Error); }
bool UWarAbilityWorkshopWidget::VerifyAnalysis(FString& Error)
{ return Workshop && Workshop->VerifyAnalysis(Error); }
bool UWarAbilityWorkshopWidget::VerifyReview(FString& Error)
{ return Workshop && Workshop->VerifyReview(Error); }
