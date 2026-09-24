#pragma once
#include "WarAbilityConditions.h"
class AActor;
class AWarCharacter;

namespace WarAbilityExecution
{
    AEGISWAR_API bool Allied(const AWarCharacter* Caster, const AActor* Target, float Range, bool bSight=true);
    AEGISWAR_API FWarCombatObservation Observe(const AActor* Actor);
    AEGISWAR_API FWarConditionContext Capture(AWarCharacter* Caster, AActor* Target, AActor* Recipient, double Now);
    AEGISWAR_API void Apply(const FWarAbilityEffect& Effect, float Amount, AWarCharacter* Caster, AActor* Recipient,
        AActor* SelectedTarget, const TSharedPtr<const FWarAbilityDefinition>& Ability, float Strength, int32 Level, bool bBonus=false, bool bRequireSight=true);
}
