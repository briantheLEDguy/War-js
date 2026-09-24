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
    UPROPERTY(EditAnywhere, Category="Siege") int32 DefinitionVersion = 1;
    UPROPERTY(EditAnywhere, Category="Siege") FName Capital = TEXT("aegis_capital");
    UPROPERTY(EditAnywhere, Category="Siege") TArray<FWarSiegeRosterEntry> Roster;
    // Stage 0: supply, checkpoint 1, checkpoint 2, breach; stage 1: two mechanisms, controls; stage 2: commander.
    UPROPERTY(EditAnywhere, Category="Siege", meta=(MakeEditWidget=true)) TArray<FVector> Objectives;
    UPROPERTY(EditAnywhere, Category="Siege", meta=(MakeEditWidget=true)) TArray<FVector> OptionalObjectives;
    // Aegis then Riftbound for each stage.
    UPROPERTY(EditAnywhere, Category="Siege", meta=(MakeEditWidget=true)) TArray<FVector> TeamSpawns;
    UPROPERTY(EditAnywhere, Category="Siege") TSoftObjectPtr<UWarCharacterVisualDefinition> CrewVisual;
    UPROPERTY(EditAnywhere, Category="Siege") TSoftObjectPtr<UWarCharacterVisualDefinition> GuardVisual;
    UPROPERTY(EditAnywhere, Category="Siege") TSoftObjectPtr<UWarCharacterVisualDefinition> CommanderVisual;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TObjectPtr<AActor>> StageGates;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TObjectPtr<AActor>> GateMechanisms;
    UPROPERTY(EditAnywhere, Category="Siege") TArray<TObjectPtr<AActor>> WarEffortProps;
    UPROPERTY(EditAnywhere, Category="Siege") float ObjectiveRadius = 650;
    UPROPERTY(EditAnywhere, Category="Siege") float ReferenceDamagePerSecond = 50;
    UPROPERTY(EditAnywhere, Category="Siege") bool bTraversalReviewed = false;
    UPROPERTY(EditAnywhere, Category="Siege") bool bEquippedRosterReviewed = false;
    bool Validate(FString& Error) const;
    FVector Objective(int32 Stage, int32 Step) const;
    void ApplyMilestones(const FWarSiegeState& State);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
private:
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
};
