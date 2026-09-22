#pragma once

#include "CoreMinimal.h"
#include "AttributeSet.h"
#include "AbilitySystemComponent.h"
#include "WarAttributeSet.generated.h"

#define WAR_ATTRIBUTE_ACCESSORS(Property) \
    GAMEPLAYATTRIBUTE_PROPERTY_GETTER(UWarAttributeSet, Property) \
    GAMEPLAYATTRIBUTE_VALUE_GETTER(Property) \
    GAMEPLAYATTRIBUTE_VALUE_SETTER(Property) \
    GAMEPLAYATTRIBUTE_VALUE_INITTER(Property)

UCLASS()
class AEGISWAR_API UWarAttributeSet : public UAttributeSet
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly, ReplicatedUsing=OnRep_Health, Category="Vitals") FGameplayAttributeData Health;
    UPROPERTY(BlueprintReadOnly, ReplicatedUsing=OnRep_MaxHealth, Category="Vitals") FGameplayAttributeData MaxHealth;
    UPROPERTY(BlueprintReadOnly, ReplicatedUsing=OnRep_Mana, Category="Vitals") FGameplayAttributeData Mana;
    UPROPERTY(BlueprintReadOnly, ReplicatedUsing=OnRep_MaxMana, Category="Vitals") FGameplayAttributeData MaxMana;
    WAR_ATTRIBUTE_ACCESSORS(Health)
    WAR_ATTRIBUTE_ACCESSORS(MaxHealth)
    WAR_ATTRIBUTE_ACCESSORS(Mana)
    WAR_ATTRIBUTE_ACCESSORS(MaxMana)

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
    virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;
    virtual bool PreGameplayEffectExecute(FGameplayEffectModCallbackData& Data) override;
private:
    UFUNCTION() void OnRep_Health(const FGameplayAttributeData& Previous);
    UFUNCTION() void OnRep_MaxHealth(const FGameplayAttributeData& Previous);
    UFUNCTION() void OnRep_Mana(const FGameplayAttributeData& Previous);
    UFUNCTION() void OnRep_MaxMana(const FGameplayAttributeData& Previous);
};

#undef WAR_ATTRIBUTE_ACCESSORS
