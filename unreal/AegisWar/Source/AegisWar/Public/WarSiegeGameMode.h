#pragma once
#include "CoreMinimal.h"
#include "WarGameMode.h"
#include "WarSiegeBattlefield.h"
#include "WarCharacter.h"
#include "AIController.h"
#include "WarSiegeGameMode.generated.h"

UCLASS()
class AEGISWAR_API AWarSiegeCharacter : public AWarCharacter
{
    GENERATED_BODY()
public:
    UPROPERTY(Replicated) EWarSiegeUnit Unit = EWarSiegeUnit::Participant;
    UPROPERTY(Replicated) TObjectPtr<class AWarSiegeEquipment> Equipment;
    float CrewMoveSpeed = 100;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
};

UCLASS()
class AEGISWAR_API AWarSiegeBotController : public AAIController
{
    GENERATED_BODY()
public:
    AWarSiegeBotController(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void Tick(float Delta) override;
    EWarSiegeRole CombatRole = EWarSiegeRole::Damage;
    EWarSiegeUnit Unit = EWarSiegeUnit::Participant;
    // A new birth identity prevents recovered effects from retargeting a replacement NPC.
    FString CampaignCombatSourceKey;
    TWeakObjectPtr<AController> Leader;
    UPROPERTY() TObjectPtr<UWarCharacterVisualDefinition> Visual;
    bool bOptionalTask = false;
    int32 ObjectiveSide = 0;
    FVector PreviousLocation = FVector::ZeroVector;
    FVector LastMoveGoal = FVector::ZeroVector;
    double StalledSeconds = 0;
private:
    bool bRecovering = false;
    EWarSiegeDecision LastDecision = EWarSiegeDecision::Follow;
};

UCLASS()
class AEGISWAR_API AWarSiegeGameMode : public AWarGameMode
{
    GENERATED_BODY()
public:
    AWarSiegeGameMode();
    virtual void BeginPlay() override;
    virtual void PreLogin(const FString& Options, const FString& Address, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage) override;
    virtual void PreLoginAsync(const FString& Options,const FString& Address,const FUniqueNetIdRepl& UniqueId,const FOnPreLoginCompleteDelegate& OnComplete) override;
    virtual APlayerController* Login(UPlayer* NewPlayer,ENetRole InRemoteRole,const FString& Portal,const FString& Options,const FUniqueNetIdRepl& UniqueId,FString& ErrorMessage) override;
    virtual void Logout(AController* Exiting) override;
    virtual void Tick(float Delta) override;
    virtual void HandleStartingNewPlayer_Implementation(APlayerController* Player) override;
    virtual APawn* SpawnDefaultPawnAtTransform_Implementation(AController* Player, const FTransform& Transform) override;
    virtual void RestartPlayer(AController* Player) override;
    virtual void RespawnAfterDeath(AWarCharacter* Character) override;
    bool Launch(class AWarPlayerController* Gm, int32 Capacity, int32 Seed, FString& Error);
    bool ResetSiege(class AWarPlayerController* Gm, FString& Error);
    bool IsDevelopmentPlaytest() const;
    bool IsMenuScenario() const;
    bool SetReady(class AWarPlayerController* Player, int32 ExpectedRound, bool bReady, FString& Error);
    bool SelectRole(class AWarPlayerController* Player, int32 ExpectedRound, EWarSiegeRole CombatRole, FString& Error);
    UWarCharacterVisualDefinition* SelectedVisual(AController* Player) const;
    bool IsProtected(const AActor* Actor) const;
    bool IsParticipant(const AWarCharacter* Pawn) const;
    FVector TaskLocation() const;
    class AWarSiegeEncounter* SiegeState() const;
    UPROPERTY() TObjectPtr<class AWarSiegeEncounter> Encounter;
    void CommanderDamaged();
    UPROPERTY() TObjectPtr<AWarSiegeBattlefield> Battlefield;
private:
    bool Authorized(class AWarPlayerController* Gm, FString& Error) const;
    bool StartRound(int32 Capacity, int32 Seed, EWarSiegeScenario Scenario, FString& Error);
    bool FindBattlefield(FString& Error);
    void UpdateLobby();
    void ClearRoundEffects();
    TMap<TWeakObjectPtr<AController>, TWeakObjectPtr<UWarCharacterVisualDefinition>> Selections;
    double NextLobbyCheck = 0;
    int32 DevelopmentJoins = 0;
    void Wave();
    bool ValidateEquipmentStaging(FString& Error);
    void ClearUnits(bool bParticipants);
    void Publish();
};
