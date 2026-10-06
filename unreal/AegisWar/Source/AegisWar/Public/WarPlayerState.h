#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerState.h"
#include "AbilitySystemInterface.h"
#include "ActiveGameplayEffectHandle.h"
#include "WarTypes.h"
#include "WarInventorySnapshot.h"
#include "WarSiegeRules.h"
#include "WarPlayerState.generated.h"

class UAbilitySystemComponent;
class UWarAttributeSet;
class AWarCharacter;
class AWarCraftingStation;
class AWarResourceNode;
class AWarCityNpc;
class AWarQuestNpc;
struct FWarQuestDefinition;
struct FGameplayEffectSpec;
struct FActiveGameplayEffect;

/** PlayerState owns GAS so replacing the pawn does not clear ability cooldowns. */
UCLASS()
class AEGISWAR_API AWarPlayerState : public APlayerState, public IAbilitySystemInterface
{
    GENERATED_BODY()
public:
    AWarPlayerState();
    virtual void PostInitializeComponents() override;
    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    const UWarAttributeSet* GetAttributes() const { return Attributes; }
    class UWarAbilityRuntime* GetClassAbilities() const { return ClassAbilities; }
    bool GetCampaignEffectEpoch(FActiveGameplayEffectHandle Handle,int64& Expiry) const;
    bool RestoreCampaignEffectEpoch(FActiveGameplayEffectHandle Handle,int64 Expiry);
    EWarRealm GetRealm() const { return Realm; }
    FName GetCurrentZone() const { return CurrentZone; }
    void SetCurrentZoneTrusted(FName Zone);
    void SetDevelopmentRealm(EWarRealm InRealm);
    void InitializeForPawn(AWarCharacter* Avatar);
    void RestoreScenarioInventory(const FWarInventorySnapshot& Snapshot);
    bool IsScenarioTransferPending() const { return bScenarioTransferPending; }
    void SetScenarioTransferPending(bool Pending);
    TSharedPtr<class FJsonObject> CaptureScenarioState() const;
    void RestoreScenarioState(const TSharedPtr<class FJsonObject>& State);
    TSharedPtr<class FJsonObject> CaptureCampaignState(FString& Error) const;
    bool RestoreCampaignState(const TSharedPtr<class FJsonObject>& State,FString& Error,bool Respawn=false,int64 CurrentUtc=0);
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
    int32 GetCombatLevel() const { return bSiegeNormalized ? 40 : Inventory.CharacterProgression.Level; }
    int32 GetAbilityUnlockLevel() const { return bScenarioEarnedAbilities ? Inventory.CharacterProgression.Level : GetCombatLevel(); }
    void UseScenarioEarnedAbilities() { if (HasAuthority()) bScenarioEarnedAbilities=true; }
    bool IsSiegeNormalized() const { return bSiegeNormalized; }
    void SetSiegeNormalized(bool bEnabled);
    class AWarSiegeEncounter* GetSiegeEncounter() const { return SiegeEncounter; }
    EWarSiegeUnit GetSiegeUnit() const { return SiegeUnit; }
    bool IsSiegeMember() const { return SiegeEncounter != nullptr; }
    // Normalized training fixtures also use targeted class healing.
    bool UsesSiegeTargeting() const;
    void SetSiegeMembership(class AWarSiegeEncounter* Encounter, EWarSiegeUnit Unit = EWarSiegeUnit::Participant);
    // Called by the controller only after development GM authorization; never exposed as an RPC.
    bool SetGmLevelTrusted(int32 Level, FString& Error);
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
    friend class FWarCampaignMutation;
    int32 CampaignMutationDepth = 0;
    struct FCampaignEffectEpoch { int64 Expiry=0;float WorldEnd=0,Duration=0; };
    TMap<FActiveGameplayEffectHandle,FCampaignEffectEpoch> CampaignEffectEpochs;
    void CampaignEffectAdded(UAbilitySystemComponent* Component,const FGameplayEffectSpec& Spec,FActiveGameplayEffectHandle Handle);
    void CampaignEffectRemoved(const FActiveGameplayEffect& Effect);
    TWeakObjectPtr<AWarCharacter> TransferAvatar;
    uint8 TransferMovementMode = 0, TransferCustomMode = 0;
    bool bScenarioTransferPending = false;
    UPROPERTY(Replicated) bool bSiegeNormalized = false;
    UPROPERTY(Replicated) TObjectPtr<class AWarSiegeEncounter> SiegeEncounter;
    UPROPERTY(Replicated) EWarSiegeUnit SiegeUnit = EWarSiegeUnit::Participant;
    UPROPERTY(Replicated) bool bScenarioEarnedAbilities = false;
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
