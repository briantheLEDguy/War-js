#include "WarAbilityExecution.h"
#include "WarAbilityRuntime.h"
#include "WarCombatStatus.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarPlayerState.h"
#include "Engine/World.h"

bool WarAbilityExecution::Allied(const AWarCharacter* Caster, const AActor* Target, float Range, bool bSight)
{
    const auto* Ally=Cast<AWarCharacter>(Target);
    if (!Caster || !Ally || Caster->IsDead() || Caster->GetWorld()!=Ally->GetWorld() || Ally->IsDead() || !Ally->IsVisualReady() || Ally->IsDevelopmentFlying()) return false;
    const auto* Source=Caster->GetPlayerState<AWarPlayerState>(); const auto* Other=Ally->GetPlayerState<AWarPlayerState>();
    if (!Source || !Other || Source->GetRealm()==EWarRealm::None || Source->GetRealm()!=Other->GetRealm() || Source->GetCurrentZone()!=Other->GetCurrentZone()
        || FVector::DistSquared(Caster->GetActorLocation(),Target->GetActorLocation())>FMath::Square(Range)) return false;
    if (!bSight || Caster==Target) return true;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(AbilityAlly),false,Caster);
    return !Caster->GetWorld()->LineTraceSingleByChannel(Hit,Caster->GetActorLocation(),Target->GetActorLocation(),ECC_Visibility,Query) || Hit.GetActor()==Target;
}
FWarCombatObservation WarAbilityExecution::Observe(const AActor* Actor)
{
    FWarCombatObservation Result;
    if (!IsValid(Actor)) return Result;
    Result.Id=FName(*Actor->GetPathName());
    if (const auto* Pawn=Cast<AWarCharacter>(Actor))
    {
        Result.bAlive=!Pawn->IsDead();
        if (const auto* State=Pawn->GetPlayerState<AWarPlayerState>())
        {
            Result.Realm=State->GetRealm()==EWarRealm::Aegis ? FName(TEXT("aegis")) : State->GetRealm()==EWarRealm::Riftbound ? FName(TEXT("riftbound")) : NAME_None;
            if (const auto* Runtime=State->GetClassAbilities()) { Result.CastingAbility=Runtime->GetCastingAbility(); Result.ActionState=Runtime->GetActionState(); }
        }
    }
    else if (const auto* Enemy=Cast<AWarEnemy>(Actor)) Result.bAlive=!Enemy->IsDead();
    if (const auto* Status=UWarCombatStatus::On(Actor)) Result.Statuses=Status->Observe();
    return Result;
}
FWarConditionContext WarAbilityExecution::Capture(AWarCharacter* Caster, AActor* Target, AActor* Recipient, double Now)
{ FWarConditionContext Result; Result.Now=Now; Result.Caster=Observe(Caster); Result.Target=Observe(Target); Result.Recipient=Observe(Recipient); return Result; }
void WarAbilityExecution::Apply(const FWarAbilityEffect& Effect, float Amount, AWarCharacter* Caster, AActor* Recipient,
    AActor* SelectedTarget, const TSharedPtr<const FWarAbilityDefinition>& Ability, float Strength, int32 Level, bool bBonus, bool bRequireSight)
{
    if (!Caster || !Caster->HasAuthority() || !IsValid(Recipient) || !Ability) return;
    const float Range=Ability->Range+Ability->Radius+100;
    const bool Harmful=Effect.Kind==TEXT("damage") || Effect.Kind==TEXT("status");
    if (Harmful ? !Caster->CanAbilityTarget(Recipient,Range,bRequireSight) : !Allied(Caster,Recipient,Range,bRequireSight)) return;
    if (Effect.PeriodicDuration>0)
    {
        if (auto* Status=UWarCombatStatus::On(Recipient)) Status->ApplyPeriodic(Effect,Amount,Caster,SelectedTarget,Ability,Strength,Level,bBonus);
    }
    else if (Effect.Kind==TEXT("damage")) UWarCombatStatus::Damage(Recipient,Caster,Amount,Range,bRequireSight);
    else if (Effect.Kind==TEXT("heal")) UWarCombatStatus::Heal(Cast<AWarCharacter>(Recipient),Amount);
    else if (Effect.Kind==TEXT("cleanse")) { if (auto* Status=UWarCombatStatus::On(Recipient)) Status->Cleanse(Effect.Cleanse); }
    else if (Effect.Kind==TEXT("status") || Effect.Kind==TEXT("player_status"))
    { if (auto* Status=UWarCombatStatus::On(Recipient)) Status->Apply(Effect,Ability->Id,Caster,Strength,Level,Ability->Version,Amount); }
}
