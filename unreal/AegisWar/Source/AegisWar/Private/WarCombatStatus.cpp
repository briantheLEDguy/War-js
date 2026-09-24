#include "WarCombatStatus.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarGameplayEffects.h"
#include "WarAbilityExecution.h"
#include "WarAbilityRuntime.h"
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
void UWarCombatStatus::Apply(const FWarAbilityEffect& Effect, FName AbilityId, AWarCharacter* Source, float Strength, int32 Level, const FString& Version,float AuthoredAmount)
{
    if (!GetOwner()->HasAuthority() || Effect.Duration <= 0) return;
    FWarActiveStatus Status;
    Status.Id = FName(*(AbilityId.ToString() + TEXT(":") + Effect.StatusId.ToString() + TEXT(":") + Effect.StatusKind.ToString()));
    Status.AbilityId=AbilityId; Status.EffectId=Effect.Id; Status.AppliedVersion=Version;
    Status.SourceCombatant=Source ? FName(*Source->GetPathName()) : NAME_None;
    if (const auto* State=Source ? Source->GetPlayerState<AWarPlayerState>() : nullptr)
        Status.SourceRealm=State->GetRealm()==EWarRealm::Aegis ? FName(TEXT("aegis")) : State->GetRealm()==EWarRealm::Riftbound ? FName(TEXT("riftbound")) : NAME_None;
    Status.Category=Effect.StatusKind==TEXT("shield") ? TEXT("shield") : Effect.StatusKind==TEXT("burn") || Effect.StatusKind==TEXT("bleed") ? TEXT("dot") : TEXT("status");
    if (!Effect.Recipient.IsNone()) Status.Id=FName(*(AbilityId.ToString()+TEXT(":")+Effect.Id.ToString()+TEXT(":")+Status.SourceCombatant.ToString()));
    Status.Kind = Effect.StatusKind; Status.Label = Effect.Label.IsEmpty() ? Effect.StatusKind.ToString() : Effect.Label;
    Status.Group = Effect.StackGroup; Status.Modifier = Effect.Modifier;
    Status.Magnitude = FMath::Clamp(Effect.Magnitude, 0.f, Status.Kind == TEXT("guard") ? .75f : .6f);
    Status.Expires = Now() + FMath::Clamp(Effect.Duration, 0.f, 60.f); Status.NextTick = Now() + 1; Status.Source = Source;
    if (Status.Kind == TEXT("burn") || Status.Kind == TEXT("bleed")) Status.TickDamage = FMath::Max(1.f, FMath::RoundToFloat(Strength * Status.Magnitude + Level * .5f));
    if (Status.Kind == TEXT("shield"))
    {
        const auto* Player = Cast<AWarCharacter>(GetOwner()); const auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        if (State && State->GetAttributes()) Status.Shield = State->GetAttributes()->GetMaxHealth() * Status.Magnitude;
        if (Effect.bHasAmount && AuthoredAmount>=0) Status.Shield=AuthoredAmount;
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
{ if (GetOwner()->HasAuthority()) { Active.Reset(); Periodic.Reset(); GetOwner()->ForceNetUpdate(); } }

TArray<FWarStatusObservation> UWarCombatStatus::Observe() const
{
    TArray<FWarStatusObservation> Result;
    for (const auto& S : Active)
    { FWarStatusObservation O; O.AbilityId=S.AbilityId; O.EffectId=S.EffectId; O.SourceId=S.SourceCombatant; O.SourceRealm=S.SourceRealm; O.Category=S.Category; O.Expires=S.Expires; O.Remaining=S.Shield; Result.Add(O); }
    return Result;
}
void UWarCombatStatus::ApplyPeriodic(const FWarAbilityEffect& Effect, float Base, AWarCharacter* Source, AActor* SelectedTarget,
    const TSharedPtr<const FWarAbilityDefinition>& Ability, float Strength, int32 Level, bool bBonus)
{
    if (!GetOwner()->HasAuthority() || !IsValid(Source) || !Ability || Effect.PeriodicDuration<=0 || Effect.Interval<.1f || !FMath::IsFinite(Base)) return;
    FWarActiveStatus Status;
    Status.AbilityId=Ability->Id; Status.EffectId=Effect.Id; Status.Source=Source; Status.SourceCombatant=FName(*Source->GetPathName()); Status.AppliedVersion=Ability->Version;
    Status.Id=FName(*(Ability->Id.ToString()+TEXT(":")+Effect.Id.ToString()+TEXT(":")+Status.SourceCombatant.ToString()));
    Status.Category=Effect.Kind==TEXT("heal") ? TEXT("hot") : TEXT("dot"); Status.Kind=Status.Category;
    Status.Label=Ability->Name; Status.Expires=Now()+Effect.PeriodicDuration; Status.NextTick=Now()+Effect.Interval; Status.Interval=Effect.Interval;
    if (const auto* State=Source->GetPlayerState<AWarPlayerState>()) Status.SourceRealm=State->GetRealm()==EWarRealm::Aegis ? FName(TEXT("aegis")) : State->GetRealm()==EWarRealm::Riftbound ? FName(TEXT("riftbound")) : NAME_None;
    if (Effect.Kind==TEXT("heal")) Status.TickHealing=Base; else Status.TickDamage=Base;
    Active.RemoveAll([&](const auto& S) { return S.Id==Status.Id || S.Expires<=Now(); });
    if (Active.Num()>=128) return;
    Active.Add(Status);
    FPeriodicExecution Execution; Execution.Ability=Ability; Execution.Effect=Effect; Execution.Target=SelectedTarget;
    Execution.Base=Base; Execution.Strength=Strength; Execution.Level=Level; Execution.bBonus=bBonus;
    Periodic.Add(Status.Id,MoveTemp(Execution)); GetOwner()->ForceNetUpdate();
}
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
    // Snapshot every due evaluation before applying any tick to avoid same-event self-triggering.
    TArray<FWarActiveStatus> Ticks;
    TMap<FName,FPeriodicExecution> Executions;
    TMap<FName,FWarRuleEvaluation> Evaluations;
    for (auto& S : Active) if ((S.TickDamage>0 || S.TickHealing>0 || Periodic.Contains(S.Id)) && S.NextTick<=Now() && S.NextTick<=S.Expires)
    {
        Ticks.Add(S); S.NextTick+=S.Interval;
        if (const auto* Execution=Periodic.Find(S.Id))
        {
            Executions.Add(S.Id,*Execution);
            if (!Execution->bBonus) Evaluations.Add(S.Id,WarAbilityConditions::Evaluate(Execution->Ability->Conditions,TEXT("tick"),WarAbilityExecution::Capture(S.Source,Execution->Target.Get(),GetOwner(),Now())));
        }
    }
    Active.RemoveAll([&](const auto& S) { return S.Expires <= Now() || (S.Kind == TEXT("shield") && S.Shield <= 0); });
    for (const auto& S : Ticks) if (IsValid(S.Source))
    {
        const auto* Execution=Executions.Find(S.Id);
        if (!Execution) { Damage(GetOwner(),S.Source,S.TickDamage,5000,false); continue; }
        const auto* Evaluation=Evaluations.Find(S.Id);
        const float Amount=Evaluation ? WarAbilityConditions::Amount(Execution->Base,S.EffectId,{*Evaluation}) : Execution->Base;
        FWarAbilityEffect Immediate=Execution->Effect; Immediate.PeriodicDuration=0;
        WarAbilityExecution::Apply(Immediate,Amount,S.Source,GetOwner(),Execution->Target.Get(),Execution->Ability,Execution->Strength,Execution->Level,true,false);
        if (Evaluation)
        {
            if (auto* State=S.Source->GetPlayerState<AWarPlayerState>()) State->GetClassAbilities()->RecordConditions(Evaluation->Traces);
            for (const auto& Bonus : Evaluation->BonusEffects)
            {
                AActor* Recipient=Bonus.Recipient==TEXT("caster") ? S.Source.Get() : GetOwner();
                const float BonusAmount=WarAbilityConditions::Amount(WarAbilities::RawAmount(Bonus,Execution->Strength,Execution->Level,0,FMath::FRand()),Bonus.Id,{});
                WarAbilityExecution::Apply(Bonus,BonusAmount,S.Source,Recipient,Execution->Target.Get(),Execution->Ability,Execution->Strength,Execution->Level,true,false);
            }
        }
    }
    for (auto It=Periodic.CreateIterator(); It; ++It) if (!Active.ContainsByPredicate([&](const auto& S) { return S.Id==It.Key(); })) It.RemoveCurrent();
}
