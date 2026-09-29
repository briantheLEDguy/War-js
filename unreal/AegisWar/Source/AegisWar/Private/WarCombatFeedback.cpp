#include "WarCombatFeedback.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarEnemy.h"

bool WarCombatFeedback::Valid(FName Kind, float Amount)
{
    return FMath::IsFinite(Amount) && Amount >= 0 && Amount <= 1.e9f
        && (Kind == TEXT("Interrupt") || ((Kind == TEXT("Hit") || Kind == TEXT("Heal") || Kind == TEXT("Guarded")) && Amount > 0));
}
bool WarCombatFeedback::Append(TArray<FWarCombatNotice>& Notices, uint32& LastSerial, uint32 Serial,
    FName Kind, const FString& Label, float Amount, double Now)
{
    if (!Serial || Serial <= LastSerial || !Valid(Kind, Amount) || !FMath::IsFinite(Now)) return false;
    LastSerial = Serial;
    Notices.RemoveAll([Now](const auto& Notice) { return Notice.Expires <= Now; });
    while (Notices.Num() >= 6) Notices.RemoveAt(0);
    Notices.Add({Kind, Label.Left(80), Amount, Now + 3});
    return true;
}
void WarCombatFeedback::Emit(AActor* Source, AActor* Target, FName Kind, float Amount)
{
    if (!IsValid(Target) || !Target->HasAuthority() || !Valid(Kind, Amount)) return;
    const auto Name = [](AActor* Actor) {
        if (const auto* Pawn = Cast<AWarCharacter>(Actor))
            if (const auto* State = Pawn->GetPlayerState<AWarPlayerState>()) return State->GetPlayerName();
        if (const auto* Enemy = Cast<AWarEnemy>(Actor)) return Enemy->GetDefinition().Name;
        return FString(TEXT("Combatant"));
    };
    auto* From = Cast<APawn>(Source); auto* To = Cast<APawn>(Target);
    auto* SourcePlayer = From ? Cast<AWarPlayerController>(From->GetController()) : nullptr;
    auto* TargetPlayer = To ? Cast<AWarPlayerController>(To->GetController()) : nullptr;
    if (SourcePlayer) SourcePlayer->SendCombatNotice(Kind, Name(Target), Amount);
    if (TargetPlayer && TargetPlayer != SourcePlayer) TargetPlayer->SendCombatNotice(Kind, Name(Source), Amount);
}
