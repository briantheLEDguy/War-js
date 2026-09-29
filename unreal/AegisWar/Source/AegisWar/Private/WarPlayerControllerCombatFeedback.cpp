#include "WarPlayerController.h"
#include "Engine/World.h"

void AWarPlayerController::SendCombatNotice(FName Kind, const FString& Label, float Amount)
{
    if (GetWorld()->GetTimeSeconds() >= CombatNoticeWindow)
    { CombatNoticeWindow = GetWorld()->GetTimeSeconds() + 1; CombatNoticeCount = 0; }
    if (CombatNoticeCount >= 20) return;
    if (HasAuthority() && WarCombatFeedback::Valid(Kind, Amount) && NextCombatSerial < MAX_uint32)
    { ++CombatNoticeCount; ClientCombatNotice(++NextCombatSerial, Kind, Label.Left(80), Amount); }
}
void AWarPlayerController::ClientCombatNotice_Implementation(uint32 Serial, FName Kind, const FString& Label, float Amount)
{
    WarCombatFeedback::Append(CombatNotices, LastCombatSerial, Serial, Kind, Label, Amount, GetWorld()->GetTimeSeconds());
}
