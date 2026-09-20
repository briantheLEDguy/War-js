#include "WarStrikeAbility.h"
#include "WarCharacter.h"
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
    AWarCharacter* Target = Attacker ? Attacker->GetRequestedStrikeTarget() : nullptr;
    // Revalidate immediately before cost and cooldown; the client never supplies damage, resource or range.
    if (!Attacker || !Attacker->HasAuthority() || !Attacker->CanStrikeTarget(Target)
        || !CommitAbility(Handle, ActorInfo, ActivationInfo))
    {
        EndAbility(Handle, ActorInfo, ActivationInfo, true, true);
        return;
    }
    UAbilitySystemComponent* Source = Attacker->GetAbilitySystemComponent();
    UAbilitySystemComponent* Destination = Target->GetAbilitySystemComponent();
    const FGameplayEffectSpecHandle Damage = Source->MakeOutgoingSpec(UWarStrikeDamageEffect::StaticClass(), 1.f, Source->MakeEffectContext());
    if (Damage.IsValid()) Source->ApplyGameplayEffectSpecToTarget(*Damage.Data.Get(), Destination);
    Attacker->MulticastPlayStrike();
    EndAbility(Handle, ActorInfo, ActivationInfo, true, false);
}
