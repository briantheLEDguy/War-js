#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/GameStateBase.h"
#include "WarSiegeRules.h"
#include "WarTypes.h"
#include "WarSiegeBattlefield.generated.h"
class UWarCharacterVisualDefinition;

USTRUCT(BlueprintType)
struct FWarSiegeRosterEntry
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) EWarRealm Realm = EWarRealm::None;
    UPROPERTY(EditAnywhere) EWarSiegeRole CombatRole = EWarSiegeRole::Damage;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UWarCharacterVisualDefinition> Visual;
};

/** Siege-only map authoring contract. Positions are world-space centimetres. */
UCLASS()
class AEGISWAR_API AWarSiegeBattlefield : public AActor
{
    GENERATED_BODY()
public:
    AWarSiegeBattlefield();
    UPROPERTY(EditAnywhere) bool bLiveCapitalOverlay = false;
    UPROPERTY(EditAnywhere, Category="Siege") int32 DefinitionVersion = 1;
    UPROPERTY(EditAnywhere, Category="Siege") FName Capital = TEXT("aegis_capital");
    UPROPERTY(EditAnywhere, Category="Siege") TObjectPtr<class UWarCityDefinition> CityDefinition;
    UPROPERTY(EditAnywhere, Category="Siege") FString ReviewedCityRevision;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<FWarSiegeRosterEntry> Roster;
    // v1: sequential mechanisms/controls. v2: independent left/right sides, central plaza. Both retain eight anchors.
    UPROPERTY(EditAnywhere, Category="Siege", meta=(MakeEditWidget=true)) TArray<FVector> Objectives;
    UPROPERTY(EditAnywhere, Category="Siege", meta=(MakeEditWidget=true)) TArray<FVector> OptionalObjectives;
    // Aegis then Riftbound for each stage.
    UPROPERTY(EditAnywhere, Category="Siege", meta=(MakeEditWidget=true)) TArray<FVector> TeamSpawns;
    UPROPERTY(EditAnywhere, Category="Siege") TSoftObjectPtr<UWarCharacterVisualDefinition> CrewVisual;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TSoftObjectPtr<class UWarSiegeEquipmentDefinition>> EquipmentDefinitions;
    UPROPERTY(EditAnywhere, Category="Siege", meta=(MakeEditWidget=true)) TArray<FVector> EquipmentSpawns;
    UPROPERTY(EditAnywhere, Category="Siege") TSoftObjectPtr<UWarCharacterVisualDefinition> GuardVisual;
    UPROPERTY(EditAnywhere, Category="Siege") TSoftObjectPtr<UWarCharacterVisualDefinition> CommanderVisual;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TObjectPtr<AActor>> StageGates;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TObjectPtr<AActor>> GateMechanisms;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TObjectPtr<AActor>> WarEffortProps;
    // Eight main and three optional Riftbound standards. Replicated claims drive visibility.
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TObjectPtr<AActor>> AttackerStandards;
    UPROPERTY(EditAnywhere, Category="Siege") float ObjectiveRadius = 650;
    UPROPERTY(EditAnywhere, Category="Siege") float ReferenceDamagePerSecond = 50;
    UPROPERTY(EditAnywhere, Category="Siege") bool bTraversalReviewed = false;
    UPROPERTY(EditAnywhere, Category="Siege") bool bEquippedRosterReviewed = false;
    // The local lower-city review cannot approve either later siege stage.
    UPROPERTY(EditAnywhere, Category="Siege") bool bLowerCityReviewed = false;
    bool IsScenarioReviewed(EWarSiegeScenario Scenario) const;
    TSubclassOf<class UNavigationQueryFilter> NavigationFilter() const;
    bool Validate(FString& Error, EWarSiegeScenario Scenario = EWarSiegeScenario::FullSiege, bool bLiveCampaign = false) const;
    FVector Objective(int32 Stage, int32 Step) const;
    FVector EquipmentDestination(int32 Step) const;
    void ApplyMilestones(const FWarSiegeState& State);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
private:
    virtual void BeginPlay() override;
    UPROPERTY(ReplicatedUsing=OnRep_Ownership) uint16 ClaimedObjectives = 0;
    UFUNCTION() void OnRep_Ownership();
    UPROPERTY(ReplicatedUsing=OnRep_Gates) uint8 OpenGates = 0;
    UFUNCTION() void OnRep_Gates();
};

UCLASS()
class AEGISWAR_API AWarSiegeGameState : public AGameStateBase
{
    GENERATED_BODY()
public:
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) FWarSiegeState Siege;
    UPROPERTY(Replicated) FString Status;
    UPROPERTY(Replicated) double NextWaveAt = 0;
    UPROPERTY(Replicated) FVector ObjectiveLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) FVector OptionalLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) FVector HazardLocation = FVector::ZeroVector;
    UPROPERTY(Replicated) double HazardUntil = 0;
    UPROPERTY(Replicated) FString CommanderAction;
    UPROPERTY(Replicated) TArray<FString> RosterLabels;
    UPROPERTY(Replicated) bool bDevelopmentLobby = false;
    UPROPERTY(Replicated) bool bQueuedScenario = false;
    UPROPERTY(Replicated) bool bContentReady = false;
    UPROPERTY(Replicated) int32 RoundId = 0;
    UPROPERTY(Replicated) TArray<int32> ReadyPlayers;
    UPROPERTY(Replicated) float CrewHealth = 0;
    UPROPERTY(Replicated) float CrewMaxHealth = 0;
    UPROPERTY(Replicated) bool bContested = false;
    UPROPERTY(Replicated) int32 Deaths = 0;
};
