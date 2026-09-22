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
class AWarCraftingStation;
class AWarResourceNode;
class AWarCityNpc;
class AWarQuestNpc;
struct FWarQuestDefinition;

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
    class UWarAbilityRuntime* GetClassAbilities() const { return ClassAbilities; }
    EWarRealm GetRealm() const { return Realm; }
    FName GetCurrentZone() const { return CurrentZone; }
    void SetCurrentZoneTrusted(FName Zone);
    void SetDevelopmentRealm(EWarRealm InRealm);
    void InitializeForPawn(AWarCharacter* Avatar);
    const FWarInventorySnapshot& GetInventory() const { return Inventory; }
    // Trusted server API only. Receipts live for this PlayerState session, not across reconnects.
    bool GrantRewards(const FGuid& Transaction, const TArray<FWarInventoryItem>& Rewards, FString& Error);
    bool TradeWithCityNpc(const AWarCityNpc* Npc, const FGuid& Transaction, FName ItemKey,
        bool bSell, int32 Quantity, int32 BagSlot, int32 ExpectedRevision, FString& Error);
    UFUNCTION(Server, Reliable) void ServerTradeWithCityNpc(AWarCityNpc* Npc, FGuid Transaction, FName ItemKey,
        bool bSell, int32 Quantity, int32 BagSlot, int32 ExpectedRevision);
    bool GrantCharacterRewards(const FGuid& Transaction, int32 Xp, int32 Gold,
        const TArray<FWarInventoryItem>& Rewards, FString& Error);
    int64 GetEffectiveStrength() const;
    // Trusted zone/NPC/kill services only; these methods are deliberately not RPCs.
    bool AcceptCatalogQuestTrusted(FName QuestId, FName Zone, int32 ExpectedRevision, FString& Error);
    bool InteractQuest(const AWarQuestNpc* Npc, FName QuestId, bool bTurnIn, int32 ExpectedRevision, FString& Error);
    UFUNCTION(Server, Reliable) void ServerInteractQuest(AWarQuestNpc* Npc, FName QuestId, bool bTurnIn, int32 ExpectedRevision);
    UFUNCTION(Client, Reliable) void ClientQuestResult(bool bAccepted, bool bTurnIn, const FString& Error);
    bool CompleteCatalogQuestTrusted(FName QuestId, FName Zone, int32 ExpectedRevision, FString& Error);
    bool RecordCatalogQuestKillTrusted(FName Zone, const FString& EnemyName, const FGuid& KillEvent, FString& Error);
    bool AwardEnemyKillTrusted(FName Zone, FName EnemyId, const FGuid& KillEvent,
        const TArray<FWarInventoryItem>& Loot, FString& Error);
    bool AcceptQuestTrusted(const FWarQuestDefinition& Quest, FName Zone, int32 ExpectedRevision, FString& Error);
    bool RecordQuestKillTrusted(const TArray<FWarQuestDefinition>& Quests, FName Zone, const FString& EnemyName, const FGuid& KillEvent, FString& Error);
    bool CompleteQuestTrusted(const FWarQuestDefinition& Quest, FName Zone, int32 ExpectedRevision,
        const TArray<FWarInventoryItem>& ResolvedRewards, FString& Error);
    bool ChangeEquipment(int32 ExpectedRevision, int32 BagSlot, bool bEquip, FString& Error);
    // Trusted recipe/consumable/salvage callers validate gameplay eligibility before this atomic exchange.
    bool ExchangeItems(const FGuid& Transaction, int32 ExpectedRevision, const TMap<int32, int32>& ConsumedSlots,
        const TArray<FWarInventoryItem>& Outputs, FString& Error);
    UFUNCTION(Server, Reliable) void ServerChangeEquipment(int32 ExpectedRevision, int32 BagSlot, bool bEquip);
    bool UseConsumable(int32 ExpectedRevision, int32 BagSlot, FString& Error);
    UFUNCTION(Server, Reliable) void ServerUseConsumable(int32 ExpectedRevision, int32 BagSlot);
    bool SalvageItem(int32 ExpectedRevision, int32 BagSlot, FString& Error);
    UFUNCTION(Server, Reliable) void ServerSalvageItem(int32 ExpectedRevision, int32 BagSlot);
    bool CraftRecipe(FName RecipeId, int32 ExpectedRevision, const AWarCraftingStation* Station, FString& Error);
    UFUNCTION(Server, Reliable) void ServerCraftRecipe(FName RecipeId, int32 ExpectedRevision, AWarCraftingStation* Station);
    UFUNCTION(Client, Reliable) void ClientInventoryResult(bool bAccepted, const FString& Error);
    bool PlantSeed(FName SeedKey, bool bUseSoil, int32 ExpectedRevision, FString& Error);
    bool HarvestCrop(FGuid PlotId, int32 ExpectedRevision, FString& Error);
    UFUNCTION(Server, Reliable) void ServerPlantSeed(FName SeedKey, bool bUseSoil, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerHarvestCrop(FGuid PlotId, int32 ExpectedRevision);
    bool GatherResource(const AWarResourceNode* Node, int32 ExpectedRevision, FString& Error);
    UFUNCTION(Server, Reliable) void ServerGatherResource(AWarResourceNode* Node, int32 ExpectedRevision);
    FText GetInventoryMessage() const { return InventoryMessage; }
private:
    UPROPERTY(Replicated) FName CurrentZone;
    bool CanPerformInventoryAction() const;
    void ApplyProgressionVitals(bool bRestorePools);
    UPROPERTY(Transient) FText InventoryMessage;
    UPROPERTY(Replicated) FWarInventorySnapshot Inventory;
    TSet<FGuid> RewardReceipts;
    TSet<FGuid> QuestKillReceipts;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAbilitySystemComponent> AbilitySystem;
    UPROPERTY() TObjectPtr<UWarAttributeSet> Attributes;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UWarAbilityRuntime> ClassAbilities;
    UPROPERTY(Replicated) EWarRealm Realm = EWarRealm::None;
    bool bGrantedDevelopmentAbility = false;
};
