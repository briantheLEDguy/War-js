#include "WarPlayerController.h"
#include "WarCityServiceWidget.h"
#include "WarCityNpc.h"
#include "WarInventoryWidget.h"
#include "WarQuestLogWidget.h"
#include "WarWorldEditWidget.h"

void AWarPlayerController::CloseCityService()
{
    if (!CityServiceWidget || !CityServiceWidget->IsInViewport()) return;
    CityServiceWidget->RemoveFromParent();
    SetInputMode(FInputModeGameOnly());
    SetIgnoreLookInput(false); SetIgnoreMoveInput(false); bShowMouseCursor=false;
}
void AWarPlayerController::OpenCityService(AWarCityNpc* Npc)
{
    if (!IsLocalController() || !GetLocalPlayer() || !IsValid(Npc) || !Npc->CanInteract(GetPawn()) || !LastEntryFailure.IsEmpty()) return;
    CloseInterface();
    CloseCityService();
    if (InventoryWidget && InventoryWidget->IsInViewport()) ToggleInventory();
    if (QuestLogWidget && QuestLogWidget->IsInViewport()) ToggleQuestLog();
    if (WorldEditWidget && WorldEditWidget->IsInViewport()) ToggleWorldEditor();
    if (!CityServiceWidget) CityServiceWidget=CreateWidget<UWarCityServiceWidget>(this,UWarCityServiceWidget::StaticClass());
    if (!CityServiceWidget) return;
    CityServiceWidget->AddToViewport(12);
    CityServiceWidget->SetPositionInViewport(FVector2D(32,32));
    CityServiceWidget->SetDesiredSizeInViewport(FVector2D(620,650));
    CityServiceWidget->SetNpc(Npc);
    SetInputMode(FInputModeGameAndUI());
    SetIgnoreLookInput(true); SetIgnoreMoveInput(true); bShowMouseCursor=true;
}
