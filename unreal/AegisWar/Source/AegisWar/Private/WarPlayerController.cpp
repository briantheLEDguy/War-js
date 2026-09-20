#include "WarPlayerController.h"
#include "WarEntryStatusWidget.h"

void AWarPlayerController::RecordEntryFailure(const FText& Reason)
{
    if (!HasAuthority()) return;
    LastEntryFailure = Reason;
    ClientEntryRejected(Reason);
}

void AWarPlayerController::ClientEntryRejected_Implementation(const FText& Reason)
{
    LastEntryFailure = Reason;
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    if (!IsLocalController() || !GetLocalPlayer()) return;
    if (!EntryStatus) EntryStatus = CreateWidget<UWarEntryStatusWidget>(this, UWarEntryStatusWidget::StaticClass());
    if (EntryStatus)
    {
        EntryStatus->SetEntryError(Reason);
        if (!EntryStatus->IsInViewport()) EntryStatus->AddToViewport(100);
    }
    SetInputMode(FInputModeUIOnly());
    bShowMouseCursor = true;
}
