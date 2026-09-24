#pragma once
#include "CoreMinimal.h"
#include "WarGameMode.h"
#include "WarSiegeBattlefield.h"
#include "WarCharacter.h"
#include "AIController.h"
#include "WarSiegeGameMode.generated.h"

UENUM()
enum class EWarSiegeUnit : uint8 { Participant, Crew, Guard, Commander, Emplacement };

UCLASS()
class AEGISWAR_API AWarSiegeCharacter : public AWarCharacter
{
    GENERATED_BODY()
public:
    UPROPERTY(Replicated) EWarSiegeUnit Unit = EWarSiegeUnit::Participant;
    float CrewMoveSpeed = 100;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
};

UCLASS()
class AEGISWAR_API AWarSiegeBotController : public AAIController
{
    GENERATED_BODY()
public:
    AWarSiegeBotController();
    virtual void Tick(float Delta) override;
    EWarSiegeRole CombatRole = EWarSiegeRole::Damage;
    EWarSiegeUnit Unit = EWarSiegeUnit::Participant;
    TWeakObjectPtr<AController> Leader;
    UPROPERTY() TObjectPtr<UWarCharacterVisualDefinition> Visual;
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
    virtual void Tick(float Delta) override;
    virtual void HandleStartingNewPlayer_Implementation(APlayerController* Player) override;
    virtual APawn* SpawnDefaultPawnAtTransform_Implementation(AController* Player, const FTransform& Transform) override;
    virtual void RestartPlayer(AController* Player) override;
    virtual void RespawnAfterDeath(AWarCharacter* Character) override;
    bool Launch(class AWarPlayerController* Gm, int32 Capacity, int32 Seed, FString& Error);
    bool ResetSiege(class AWarPlayerController* Gm, FString& Error);
    bool IsProtected(const AActor* Actor) const;
    bool IsParticipant(const AWarCharacter* Pawn) const;
    FVector TaskLocation() const;
    AWarSiegeGameState* SiegeState() const;
    void CommanderDamaged();
    UPROPERTY() TObjectPtr<AWarSiegeBattlefield> Battlefield;
private:
    bool Authorized(class AWarPlayerController* Gm, FString& Error) const;
    void Wave();
    void AssignSquads();
    void StageStarted();
    void Encounters(float Delta);
    AWarSiegeBotController* SpawnUnit(EWarRealm Realm, EWarSiegeRole CombatRole, EWarSiegeUnit Unit,
        UWarCharacterVisualDefinition* Visual, const FVector& Position);
    void ClearUnits(bool bParticipants);
    void Publish();
    void FailMatch(const FString& Error);
    TWeakObjectPtr<AWarSiegeBotController> Crew, Commander;
    TArray<TWeakObjectPtr<AWarSiegeBotController>> Units;
    double CrewAt = 0, ReinforcementAt = 0, CommanderDamageAt = -100, CommanderEngagedAt = 0;
    double CommanderActionAt = 0, CommanderReleaseAt = 0;
    int32 CommanderSequence = 0, StartedStage = -1;
    bool bCommanderInterrupted = false;
    FRandomStream Random;
};
