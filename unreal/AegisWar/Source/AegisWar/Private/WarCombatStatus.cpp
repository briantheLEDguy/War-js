#include "WarCombatStatus.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarGameplayEffects.h"
#include "AbilitySystemComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

UWarCombatStatus::UWarCombatStatus()
{ SetIsReplicatedByDefault(true); PrimaryComponentTick.bCanEverTick = true; PrimaryComponentTick.TickInterval = .05f; }
void UWarCombatStatus::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{ Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(UWarCombatStatus, Active); }
double UWarCombatStatus::Now() const
{ const auto* State = GetWorld()->GetGameState(); return State ? State->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds(); }
UWarCombatStatus* UWarCombatStatus::On(const AActor* Actor)
{ return IsValid(Actor) ? Actor->FindComponentByClass<UWarCombatStatus>() : nullptr; }
bool UWarCombatStatus::Has(FName Kind) const
{ const double Time = Now(); return Active.ContainsByPredicate([=](const auto& S) { return S.Kind == Kind && S.Expires > Time; }); }
float UWarCombatStatus::Strongest(FName Kind) const
{ float Value = 0; for (const auto& S : Active) if (S.Kind == Kind && S.Expires > Now()) Value = FMath::Max(Value, S.Magnitude); return Value; }
float UWarCombatStatus::MovementScale() const
{ return Has(TEXT("root")) || Has(TEXT("stagger")) ? 0 : (1 + Strongest(TEXT("haste"))) * (1 - FMath::Clamp(Strongest(TEXT("slow")), 0.f, 1.f)); }
float UWarCombatStatus::OutgoingScale() const
{
    float Reduction = 0;
    for (const auto& S : Active) if (S.Expires > Now() && S.Modifier == TEXT("damage_dealt")) Reduction = FMath::Max(Reduction, S.Magnitude);
    return (1 + FMath::Min(.6f, Strongest(TEXT("empower")))) * (1 - FMath::Clamp(Reduction, 0.f, .9f));
}
float UWarCombatStatus::ReceiveDamage(float Damage)
{
    if (!GetOwner()->HasAuthority() || !FMath::IsFinite(Damage)) return 0;
    float Vulnerability = 0;
    FWarActiveStatus* Shield = nullptr;
    for (auto& S : Active) if (S.Expires > Now())
    {
        if (S.Modifier == TEXT("damage_taken")) Vulnerability = FMath::Max(Vulnerability, S.Magnitude);
        if (S.Kind == TEXT("shield") && (!Shield || S.Shield > Shield->Shield)) Shield = &S;
    }
    Damage = FMath::Max(0.f, FMath::RoundToFloat(Damage * (1 + FMath::Clamp(Vulnerability, 0.f, 1.f))
        * (1 - FMath::Min(.75f, Strongest(TEXT("guard"))))));
    if (Shield) { const float Absorbed = FMath::Min(Damage, Shield->Shield); Shield->Shield -= Absorbed; Damage -= Absorbed; }
    return Damage;
}
void UWarCombatStatus::Apply(const FWarAbilityEffect& Effect, FName AbilityId, AWarCharacter* Source, float Strength, int32 Level)
{
    if (!GetOwner()->HasAuthority() || Effect.Duration <= 0) return;
    FWarActiveStatus Status;
    Status.Id = FName(*(AbilityId.ToString() + TEXT(":") + Effect.StatusId.ToString() + TEXT(":") + Effect.StatusKind.ToString()));
    Status.Kind = Effect.StatusKind; Status.Label = Effect.Label.IsEmpty() ? Effect.StatusKind.ToString() : Effect.Label;
    Status.Group = Effect.StackGroup; Status.Modifier = Effect.Modifier;
    Status.Magnitude = FMath::Clamp(Effect.Magnitude, 0.f, Status.Kind == TEXT("guard") ? .75f : .6f);
    Status.Expires = Now() + FMath::Clamp(Effect.Duration, 0.f, 60.f); Status.NextTick = Now() + 1; Status.Source = Source;
    if (Status.Kind == TEXT("burn") || Status.Kind == TEXT("bleed")) Status.TickDamage = FMath::Max(1.f, FMath::RoundToFloat(Strength * Status.Magnitude + Level * .5f));
    if (Status.Kind == TEXT("shield"))
    {
        const auto* Player = Cast<AWarCharacter>(GetOwner()); const auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        if (State && State->GetAttributes()) Status.Shield = State->GetAttributes()->GetMaxHealth() * Status.Magnitude;
        for (const auto& S : Active) if (S.Kind == TEXT("shield") && S.Expires > Now()) Status.Shield = FMath::Max(Status.Shield, S.Shield);
    }
    Active.RemoveAll([&](const auto& S) { return S.Expires <= Now() || S.Id == Status.Id
        || (!Status.Group.IsNone() && S.Group == Status.Group) || (Status.Kind == TEXT("shield") && S.Kind == Status.Kind); });
    if (Active.Num() < 128) Active.Add(Status);
    GetOwner()->ForceNetUpdate();
}
void UWarCombatStatus::Cleanse(const TArray<FName>& Kinds)
{ if (GetOwner()->HasAuthority()) { Active.RemoveAll([&](const auto& S) { return Kinds.Contains(S.Kind); }); GetOwner()->ForceNetUpdate(); } }
void UWarCombatStatus::Clear()
{ if (GetOwner()->HasAuthority()) { Active.Reset(); GetOwner()->ForceNetUpdate(); } }
FString UWarCombatStatus::Description() const
{
    FString Result;
    for (const auto& S : Active) if (S.Expires > Now()) Result += FString::Printf(TEXT("%s %.0fs  "), *S.Label, S.Expires - Now());
    return Result;
}
bool UWarCombatStatus::Damage(AActor* Target, AWarCharacter* Source, float Amount, float Range, bool bRequireSight)
{
    if (!IsValid(Source) || !Source->HasAuthority() || !FMath::IsFinite(Amount) || Amount <= 0) return false;
    if (auto* Enemy = Cast<AWarEnemy>(Target)) return Enemy->ReceiveAbilityDamage(Source, Amount, Range, bRequireSight);
    auto* Player = Cast<AWarCharacter>(Target);
    if (!Player || !Source->CanAbilityTarget(Player, Range, bRequireSight)) return false;
    auto* ASC = Player->GetAbilitySystemComponent(); if (!ASC) return false;
    auto Context = ASC->MakeEffectContext(); Context.AddInstigator(Source, Source);
    auto Spec = ASC->MakeOutgoingSpec(UWarEnemyDamageEffect::StaticClass(), 1, Context);
    if (!Spec.IsValid()) return false;
    Spec.Data->SetSetByCallerMagnitude(FName(TEXT("WarEnemyDamage")), -Amount); ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get()); return true;
}
void UWarCombatStatus::Heal(AWarCharacter* Target, float Amount)
{
    if (!IsValid(Target) || !Target->HasAuthority() || Target->IsDead() || !FMath::IsFinite(Amount) || Amount <= 0) return;
    auto* ASC = Target->GetAbilitySystemComponent(); if (!ASC) return;
    auto Spec = ASC->MakeOutgoingSpec(UWarEnemyDamageEffect::StaticClass(), 1, ASC->MakeEffectContext());
    if (Spec.IsValid()) { Spec.Data->SetSetByCallerMagnitude(FName(TEXT("WarEnemyDamage")), Amount); ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get()); }
}
void UWarCombatStatus::TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta, TickType, Function); if (!GetOwner()->HasAuthority()) return;
    const auto* Player = Cast<AWarCharacter>(GetOwner()); const auto* Enemy = Cast<AWarEnemy>(GetOwner());
    if ((Player && Player->IsDead()) || (Enemy && Enemy->IsDead())) { Clear(); return; }
    // Copy due ticks before damage callbacks: death may clear Active during an effect.
    TArray<FWarActiveStatus> Ticks;
    for (auto& S : Active) if (S.TickDamage > 0 && S.NextTick <= Now() && S.NextTick <= S.Expires)
    { Ticks.Add(S); S.NextTick = Now() + 1; }
    Active.RemoveAll([&](const auto& S) { return S.Expires <= Now() || (S.Kind == TEXT("shield") && S.Shield <= 0); });
    for (const auto& S : Ticks) if (IsValid(S.Source)) Damage(GetOwner(), S.Source, S.TickDamage, 5000, false);
}
