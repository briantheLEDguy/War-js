#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WarAbilityCatalog.h"
#include "WarCombatStatus.generated.h"
class AWarCharacter;

USTRUCT()
struct FWarActiveStatus
{
    GENERATED_BODY()
    UPROPERTY() FName Id;
    UPROPERTY() FName Kind;
    UPROPERTY() FName Group;
    UPROPERTY() FName Modifier;
    UPROPERTY() FString Label;
    UPROPERTY() float Magnitude = 0;
    UPROPERTY() float Shield = 0;
    UPROPERTY() float TickDamage = 0;
    UPROPERTY() double Expires = 0;
    UPROPERTY() double NextTick = 0;
    UPROPERTY() TObjectPtr<AWarCharacter> Source;
};

/** Pawn-local effects expire on death; ability resources/cooldowns live on PlayerState. */
UCLASS()
class AEGISWAR_API UWarCombatStatus : public UActorComponent
{
    GENERATED_BODY()
public:
    UWarCombatStatus();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* Function) override;
    bool Has(FName Kind) const;
    float MovementScale() const;
    float OutgoingScale() const;
    float ReceiveDamage(float Damage);
    void Apply(const FWarAbilityEffect& Effect, FName AbilityId, AWarCharacter* Source, float Strength, int32 Level);
    void Cleanse(const TArray<FName>& Kinds);
    void Clear();
    FString Description() const;
    static UWarCombatStatus* On(const AActor* Actor);
    static bool Damage(AActor* Target, AWarCharacter* Source, float Amount, float Range, bool bRequireSight = true);
    static void Heal(AWarCharacter* Target, float Amount);
private:
    double Now() const;
    float Strongest(FName Kind) const;
    UPROPERTY(Replicated) TArray<FWarActiveStatus> Active;
};
