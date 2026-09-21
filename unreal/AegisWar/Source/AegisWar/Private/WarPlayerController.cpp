#include "WarPlayerController.h"
#include "WarEntryStatusWidget.h"
#include "WarInventoryWidget.h"
#include "Components/InputComponent.h"
#include "InputCoreTypes.h"

void AWarPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::I, IE_Pressed, this, &AWarPlayerController::ToggleInventory);
}

void AWarPlayerController::ToggleInventory()
{
    if (!IsLocalController() || !GetLocalPlayer() || !LastEntryFailure.IsEmpty()) return;
    if (InventoryWidget && InventoryWidget->IsInViewport())
    {
        InventoryWidget->RemoveFromParent();
        SetInputMode(FInputModeGameOnly());
        bShowMouseCursor = false;
        SetIgnoreLookInput(false);
        SetIgnoreMoveInput(false);
        return;
    }
    if (!InventoryWidget) InventoryWidget = CreateWidget<UWarInventoryWidget>(this, UWarInventoryWidget::StaticClass());
    if (!InventoryWidget) return;
    InventoryWidget->AddToViewport(10);
    InventoryWidget->SetPositionInViewport(FVector2D(32, 32));
    InventoryWidget->SetDesiredSizeInViewport(FVector2D(540, 650));
    SetInputMode(FInputModeGameAndUI());
    SetIgnoreLookInput(true);
    SetIgnoreMoveInput(true);
    bShowMouseCursor = true;
}

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
