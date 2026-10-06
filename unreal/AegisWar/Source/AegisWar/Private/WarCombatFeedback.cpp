#include "WarCombatFeedback.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarEnemy.h"

TArray<int16> WarCombatFeedback::ImpactSamples(uint32 Serial,bool bCritical)
{
    TArray<int16> Samples; Samples.SetNum(3969); FRandomStream Noise(Serial);
    for (int32 I=0;I<Samples.Num();++I)
    {
        const float T=I/static_cast<float>(ImpactSampleRate), Envelope=FMath::Exp(-T*32.f)*FMath::Min(1.f,T/.002f);
        const float Bass=FMath::Sin(2*PI*(bCritical ? 95.f : 130.f)*T);
        const float Crack=Noise.FRandRange(-1.f,1.f)*FMath::Exp(-T*90.f);
        Samples[I]=static_cast<int16>(FMath::Clamp((Bass*.55f+Crack*.4f)*Envelope,-1.f,1.f)*24000);
    }
    return Samples;
}

bool WarCombatFeedback::Valid(FName Kind, float Amount)
{
    return FMath::IsFinite(Amount) && Amount >= 0 && Amount <= 1.e9f
        && (Kind == TEXT("Interrupt") || ((Kind == TEXT("Hit") || Kind == TEXT("CriticalHit") || Kind == TEXT("Heal") || Kind == TEXT("Guarded")) && Amount > 0));
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
    if (SourcePlayer) SourcePlayer->SendCombatNotice(Kind, Name(Target), Amount, Target);
    if (TargetPlayer && TargetPlayer != SourcePlayer) TargetPlayer->SendCombatNotice(Kind, Name(Source), Amount);
}
