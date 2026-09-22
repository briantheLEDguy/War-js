#include "WarPlayerController.h"

void AWarPlayerController::ClientZoneTravelStatus_Implementation(const FString& Message)
{
    ZoneTravelStatus = Message;
}
