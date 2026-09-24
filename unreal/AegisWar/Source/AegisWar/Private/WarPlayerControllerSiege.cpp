#include "WarPlayerController.h"
#include "WarSiegeGameMode.h"
void AWarPlayerController::WarSiegeStart(int32 Capacity, int32 Seed) { ServerGmSiegeStart(Capacity, Seed); }
void AWarPlayerController::WarSiegeReset() { ServerGmSiegeReset(); }
void AWarPlayerController::ServerGmSiegeStart_Implementation(int32 Capacity, int32 Seed)
{
    FString Error;
    auto* Mode = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>();
    if (!Mode) Error = TEXT("Open the isolated Aegis siege map before launching a siege.");
    else if (Mode->Launch(this, Capacity, Seed, Error)) Error = TEXT("Bastion siege launched.");
    ClientWorldEditResult(Error);
}
void AWarPlayerController::ServerGmSiegeReset_Implementation()
{
    FString Error;
    auto* Mode = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>();
    if (!Mode) Error = TEXT("No siege is loaded.");
    else if (Mode->ResetSiege(this, Error)) Error = TEXT("Siege reset.");
    ClientWorldEditResult(Error);
}
