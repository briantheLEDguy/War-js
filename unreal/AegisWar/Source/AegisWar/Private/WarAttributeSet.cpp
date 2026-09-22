#include "WarAttributeSet.h"
#include "WarCharacter.h"
#include "WarCombatStatus.h"
#include "GameplayEffectExtension.h"
#include "Net/UnrealNetwork.h"

void UWarAttributeSet::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, Health, COND_None, REPNOTIFY_Always);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, MaxHealth, COND_None, REPNOTIFY_Always);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, Mana, COND_OwnerOnly, REPNOTIFY_Always);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, MaxMana, COND_OwnerOnly, REPNOTIFY_Always);
}

void UWarAttributeSet::PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue)
{
    Super::PreAttributeChange(Attribute, NewValue);
    if (!FMath::IsFinite(NewValue)) NewValue = 0.f;
    if (Attribute == GetHealthAttribute()) NewValue = FMath::Clamp(NewValue, 0.f, GetMaxHealth());
    if (Attribute == GetManaAttribute()) NewValue = FMath::Clamp(NewValue, 0.f, GetMaxMana());
    if (Attribute == GetMaxHealthAttribute() || Attribute == GetMaxManaAttribute()) NewValue = FMath::Max(1.f, NewValue);
}

bool UWarAttributeSet::PreGameplayEffectExecute(FGameplayEffectModCallbackData& Data)
{
    if (!Super::PreGameplayEffectExecute(Data)) return false;
    if (Data.EvaluatedData.Attribute == GetHealthAttribute() && Data.EvaluatedData.Magnitude < 0)
        if (auto* Status = UWarCombatStatus::On(GetOwningAbilitySystemComponent()->GetAvatarActor()))
            Data.EvaluatedData.Magnitude = -Status->ReceiveDamage(-Data.EvaluatedData.Magnitude);
    return true;
}

void UWarAttributeSet::PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data)
{
    Super::PostGameplayEffectExecute(Data);
    if (Data.EvaluatedData.Attribute == GetHealthAttribute())
    {
        SetHealth(FMath::Clamp(GetHealth(), 0.f, GetMaxHealth()));
        if (GetHealth() <= 0.f)
        {
            if (AWarCharacter* Avatar = Cast<AWarCharacter>(GetOwningAbilitySystemComponent()->GetAvatarActor()))
                Avatar->HandleDeath();
        }
    }
    if (Data.EvaluatedData.Attribute == GetManaAttribute()) SetMana(FMath::Clamp(GetMana(), 0.f, GetMaxMana()));
}

void UWarAttributeSet::OnRep_Health(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, Health, Previous); }
void UWarAttributeSet::OnRep_MaxHealth(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, MaxHealth, Previous); }
void UWarAttributeSet::OnRep_Mana(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, Mana, Previous); }
void UWarAttributeSet::OnRep_MaxMana(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, MaxMana, Previous); }
