#pragma once

#include "CoreMinimal.h"
#include "Abilities/GameplayAbility.h"
#include "WarStrikeAbility.generated.h"

/** Foundation demonstrator, deliberately not presented as one of the 240 migrated class abilities. */
UCLASS()
class AEGISWAR_API UWarStrikeAbility : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UWarStrikeAbility();
    virtual const FGameplayTagContainer* GetCooldownTags() const override;
    virtual void ApplyCooldown(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
        FGameplayAbilityActivationInfo ActivationInfo) const override;
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
        FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
private:
    FGameplayTagContainer CooldownTags;
};
