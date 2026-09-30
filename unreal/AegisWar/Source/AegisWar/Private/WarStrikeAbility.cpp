#include "WarStrikeAbility.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarCombatStatus.h"
#include "WarPlayerState.h"
#include "WarAbilityRuntime.h"
#include "TimerManager.h"
#include "WarGameplayEffects.h"
#include "AbilitySystemComponent.h"
#include "NativeGameplayTags.h"

UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_War_Cooldown_DevelopmentStrike, "War.Cooldown.DevelopmentStrike");

UWarStrikeAbility::UWarStrikeAbility()
{
    InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly;
    NetSecurityPolicy = EGameplayAbilityNetSecurityPolicy::ServerOnly;
    CostGameplayEffectClass = UWarStrikeCostEffect::StaticClass();
    CooldownGameplayEffectClass = UWarStrikeCooldownEffect::StaticClass();
    CooldownTags.AddTag(TAG_War_Cooldown_DevelopmentStrike);
}

const FGameplayTagContainer* UWarStrikeAbility::GetCooldownTags() const { return &CooldownTags; }

void UWarStrikeAbility::ApplyCooldown(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
    const FGameplayAbilityActivationInfo ActivationInfo) const
{
    const FGameplayEffectSpecHandle Spec = MakeOutgoingGameplayEffectSpec(Handle, ActorInfo, ActivationInfo,
        CooldownGameplayEffectClass, GetAbilityLevel(Handle, ActorInfo));
    if (Spec.IsValid())
    {
        Spec.Data->DynamicGrantedTags.AppendTags(CooldownTags);
        ApplyGameplayEffectSpecToOwner(Handle, ActorInfo, ActivationInfo, Spec);
    }
}

void UWarStrikeAbility::ActivateAbility(const FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo,
    const FGameplayEventData* TriggerEventData)
{
    AWarCharacter* Attacker = ActorInfo ? Cast<AWarCharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
    AActor* Target = Attacker ? Attacker->GetRequestedStrikeTarget() : nullptr;
    // Revalidate immediately before cost and cooldown; the client never supplies damage, resource or range.
    if (!Attacker || !Attacker->HasAuthority() || !Attacker->CanStrikeTarget(Target)
        || (Attacker->GetPlayerState<AWarPlayerState>() && (Attacker->GetPlayerState<AWarPlayerState>()->GetClassAbilities()->IsBusy() || Attacker->GetPlayerState<AWarPlayerState>()->GetClassAbilities()->Cooldown(NAME_None)>0))
        || !CommitAbility(Handle, ActorInfo, ActivationInfo))
    {
        EndAbility(Handle, ActorInfo, ActivationInfo, true, true);
        return;
    }
    const float Duration = Attacker->GetAbilityAnimationDuration(TEXT("attack_melee"));
    const TWeakObjectPtr<AActor> WeakTarget(Target);
    auto* Runtime=Attacker->GetPlayerState<AWarPlayerState>()->GetClassAbilities();
    const uint32 ActionSerial=Runtime->BeginBasicAttack(Attacker->GetBasicAttackContact());
    FTimerHandle Impact;
    Attacker->GetWorldTimerManager().SetTimer(Impact, FTimerDelegate::CreateWeakLambda(Attacker, [Attacker, WeakTarget, ActionSerial, Runtime] {
        const auto* Status = UWarCombatStatus::On(Attacker);
        if (!Attacker->IsDead() && Runtime->GetActionSerial()==ActionSerial && Attacker->CanStrikeTarget(WeakTarget.Get()) && !(Status && Status->Has(TEXT("stagger"))))
            UWarCombatStatus::Damage(WeakTarget.Get(), Attacker, WarValidation::StrikeDamage * (Status ? Status->OutgoingScale() : 1), WarValidation::StrikeRangeCm);
        Runtime->FinishBasicAttack(ActionSerial);
    }), FMath::Max(.01f, Attacker->GetBasicAttackContact()), false);
    Attacker->MulticastPlayAbilityMotion(TEXT("attack_melee"), Duration, false);
    EndAbility(Handle, ActorInfo, ActivationInfo, true, false);
}
