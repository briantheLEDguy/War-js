#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerState.h"
#include "AbilitySystemInterface.h"
#include "WarTypes.h"
#include "WarInventorySnapshot.h"
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
    const FWarInventorySnapshot& GetInventory() const { return Inventory; }
    // Trusted server API only. Receipts live for this PlayerState session, not across reconnects.
    bool GrantRewards(const FGuid& Transaction, const TArray<FWarInventoryItem>& Rewards, FString& Error);
    bool ChangeEquipment(int32 ExpectedRevision, int32 BagSlot, bool bEquip, FString& Error);
    UFUNCTION(Server, Reliable) void ServerChangeEquipment(int32 ExpectedRevision, int32 BagSlot, bool bEquip);
private:
    UPROPERTY(Replicated) FWarInventorySnapshot Inventory;
    TSet<FGuid> RewardReceipts;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAbilitySystemComponent> AbilitySystem;
    UPROPERTY() TObjectPtr<UWarAttributeSet> Attributes;
    UPROPERTY(Replicated) EWarRealm Realm = EWarRealm::None;
    bool bGrantedDevelopmentAbility = false;
};
