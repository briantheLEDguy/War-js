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
    if (!Attacker || !Attacker->HasAuthority() || !Attacker->CanStrikeTarget(Target) || Attacker->IsActionPlaying()
        || (Attacker->GetPlayerState<AWarPlayerState>() && Attacker->GetPlayerState<AWarPlayerState>()->GetClassAbilities()->IsBusy())
        || !CommitAbility(Handle, ActorInfo, ActivationInfo))
    {
        EndAbility(Handle, ActorInfo, ActivationInfo, true, true);
        return;
    }
    const float Duration = Attacker->GetAbilityAnimationDuration(TEXT("attack_melee"));
    const TWeakObjectPtr<AActor> WeakTarget(Target);
    FTimerHandle Impact;
    Attacker->GetWorldTimerManager().SetTimer(Impact, FTimerDelegate::CreateWeakLambda(Attacker, [Attacker, WeakTarget] {
        const auto* Status = UWarCombatStatus::On(Attacker);
        if (Status && Status->Has(TEXT("stagger"))) return;
        UWarCombatStatus::Damage(WeakTarget.Get(), Attacker, WarValidation::StrikeDamage * (Status ? Status->OutgoingScale() : 1), WarValidation::StrikeRangeCm);
    }), FMath::Max(.01f, Duration * (Attacker->GetAnimationProfile() == TEXT("civic_battle_prelate_m") ? .8f : .52f)), false);
    Attacker->MulticastPlayAbilityMotion(TEXT("attack_melee"), Duration, false);
    EndAbility(Handle, ActorInfo, ActivationInfo, true, false);
}
