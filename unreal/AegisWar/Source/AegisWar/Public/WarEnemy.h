#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "WarEnemyRules.h"
#include "WarEnemy.generated.h"

class AWarCharacter;
class UWarCharacterVisualDefinition;
class UStaticMeshComponent;

/** Authored source enemy. Statistics and rewards come only from the server catalog. */
UCLASS()
class AEGISWAR_API AWarEnemy : public ACharacter
{
    GENERATED_BODY()
public:
    AWarEnemy();
    virtual void BeginPlay() override;
    virtual void PostRegisterAllComponents() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(EditAnywhere, Category="Enemy") FName ZoneId;
    UPROPERTY(EditAnywhere, Category="Enemy") FName EnemyId;
    UPROPERTY(EditAnywhere, Category="Enemy") TObjectPtr<UWarCharacterVisualDefinition> Visual;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Enemy") TObjectPtr<UStaticMeshComponent> TrainingMesh;
    bool IsContentReady() const { return bReady; }
    bool IsDead() const { return Health <= 0; }
    float GetHealth() const { return Health; }
    const FWarEnemyDefinition& GetDefinition() const { return Definition; }
    FVector GetHome() const { return Home; }
    AWarCharacter* GetTarget() const { return Target.Get(); }
    bool CanReceiveStrike(const AWarCharacter* Attacker) const;
    bool CanReceiveAbility(const AWarCharacter* Attacker, float Range, bool bRequireSight = true) const;
    bool ReceiveAbilityDamage(AWarCharacter* Attacker, float Damage, float Range, bool bRequireSight = true);
    bool ReceiveStrike(AWarCharacter* Attacker);
    bool HasLineOfSight(const AActor* Actor) const;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UWarCombatStatus> CombatStatus;
    UPROPERTY(ReplicatedUsing=OnRep_Health) float Health = 0;
    UFUNCTION() void OnRep_Health();
    UFUNCTION(NetMulticast, Unreliable) void MulticastAttack();
    FWarEnemyDefinition Definition;
    FVector Home = FVector::ZeroVector;
    TWeakObjectPtr<AWarCharacter> Target;
    FName PlayingAnimation;
    bool bReady = false, bHomeCaptured = false;
    bool bPreparingEditorEquipment = false;
    double NextAttack = 0, ActionUntil = 0, NextThink = 0, BlockedSince = 0;
    FVector LastProgressPosition = FVector::ZeroVector;
    bool Eligible(const AWarCharacter* Player, double Range, bool bRequireSight) const;
    bool ResetAtHome(bool bNewLife);
    void Play(FName Clip, bool bLoop);
    void Attack(AWarCharacter* Player);
};
