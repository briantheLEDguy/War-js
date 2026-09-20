#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerState.h"
#include "AbilitySystemInterface.h"
#include "WarTypes.h"
#include "WarPlayerState.generated.h"

class UAbilitySystemComponent;
class UWarAttributeSet;
class AWarCharacter;

/** PlayerState owns GAS so replacing the pawn does not clear ability cooldowns. */
UCLASS()
class AEGISWAR_API AWarPlayerState : public APlayerState, public IAbilitySystemInterface
{
    GENERATED_BODY()
public:
    AWarPlayerState();
    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    const UWarAttributeSet* GetAttributes() const { return Attributes; }
    EWarRealm GetRealm() const { return Realm; }
    void SetDevelopmentRealm(EWarRealm InRealm);
    void InitializeForPawn(AWarCharacter* Avatar);
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAbilitySystemComponent> AbilitySystem;
    UPROPERTY() TObjectPtr<UWarAttributeSet> Attributes;
    UPROPERTY(Replicated) EWarRealm Realm = EWarRealm::None;
    bool bGrantedDevelopmentAbility = false;
};
