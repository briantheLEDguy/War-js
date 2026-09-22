#include "WarGameplayEffects.h"
#include "WarAttributeSet.h"
#include "WarTypes.h"

namespace
{
    FGameplayModifierInfo Modifier(const FGameplayAttribute& Attribute, const float Value, EGameplayModOp::Type Operation)
    {
        FGameplayModifierInfo Result;
        Result.Attribute = Attribute;
        Result.ModifierOp = Operation;
        Result.ModifierMagnitude = FGameplayEffectModifierMagnitude(FScalableFloat(Value));
        return Result;
    }
}

UWarInitialAttributesEffect::UWarInitialAttributesEffect()
{
    DurationPolicy = EGameplayEffectDurationType::Instant;
    Modifiers.Add(Modifier(UWarAttributeSet::GetMaxHealthAttribute(), 100.f, EGameplayModOp::Override));
    Modifiers.Add(Modifier(UWarAttributeSet::GetMaxManaAttribute(), 100.f, EGameplayModOp::Override));
    Modifiers.Add(Modifier(UWarAttributeSet::GetHealthAttribute(), 100.f, EGameplayModOp::Override));
    Modifiers.Add(Modifier(UWarAttributeSet::GetManaAttribute(), 100.f, EGameplayModOp::Override));
}

UWarStrikeCostEffect::UWarStrikeCostEffect()
{
    DurationPolicy = EGameplayEffectDurationType::Instant;
    Modifiers.Add(Modifier(UWarAttributeSet::GetManaAttribute(), -WarValidation::StrikeManaCost, EGameplayModOp::Additive));
}

UWarStrikeCooldownEffect::UWarStrikeCooldownEffect()
{
    DurationPolicy = EGameplayEffectDurationType::HasDuration;
    DurationMagnitude = FGameplayEffectModifierMagnitude(FScalableFloat(WarValidation::StrikeCooldownSeconds));
}

UWarStrikeDamageEffect::UWarStrikeDamageEffect()
{
    DurationPolicy = EGameplayEffectDurationType::Instant;
    Modifiers.Add(Modifier(UWarAttributeSet::GetHealthAttribute(), -WarValidation::StrikeDamage, EGameplayModOp::Additive));
}

UWarEnemyDamageEffect::UWarEnemyDamageEffect()
{
    DurationPolicy = EGameplayEffectDurationType::Instant;
    FGameplayModifierInfo Damage;
    Damage.Attribute = UWarAttributeSet::GetHealthAttribute(); Damage.ModifierOp = EGameplayModOp::Additive;
    FSetByCallerFloat Magnitude; Magnitude.DataName = TEXT("WarEnemyDamage");
    Damage.ModifierMagnitude = FGameplayEffectModifierMagnitude(Magnitude); Modifiers.Add(Damage);
}
