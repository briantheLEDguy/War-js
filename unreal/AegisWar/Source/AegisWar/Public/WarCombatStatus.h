#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityConditions.h"
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
    UPROPERTY() FName AbilityId;
    UPROPERTY() FName EffectId;
    UPROPERTY() FName SourceCombatant;
    UPROPERTY() FName SourceRealm;
    UPROPERTY() FName Category;
    UPROPERTY() FString AppliedVersion;
    UPROPERTY() float TickHealing = 0;
    UPROPERTY() float Interval = 1;
    // Server custody deadlines are fixed at application/restore, never reconstructed per capture.
    int64 ExpiresAtUnixMs = 0;
    double NextTickUnixMs = 0;
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
    void Apply(const FWarAbilityEffect& Effect, FName AbilityId, AWarCharacter* Source, float Strength, int32 Level, const FString& Version=TEXT("baseline"),float AuthoredAmount=-1,
        const TSharedPtr<const FWarAbilityDefinition>& AppliedDefinition = nullptr);
    void ApplyPeriodic(const FWarAbilityEffect& Effect, float Base, AWarCharacter* Source, AActor* SelectedTarget,
        const TSharedPtr<const FWarAbilityDefinition>& Ability, float Strength, int32 Level, bool bBonus);
    TArray<FWarStatusObservation> Observe() const;
    const TArray<FWarActiveStatus>& GetActive() const { return Active; }
    void Cleanse(const TArray<FName>& Kinds);
    void Clear();
    bool CaptureCampaignState(int64 CapturedAt, TSharedPtr<class FJsonObject>& State, FString& Error) const;
    bool RestoreCampaignState(const TSharedPtr<class FJsonObject>& State, int64 CurrentUtc, FString& Error, bool bApply = true, bool ClearForRespawn = false);
    FString Description() const;
    static UWarCombatStatus* On(const AActor* Actor);
    static bool Damage(AActor* Target, AWarCharacter* Source, float Amount, float Range, bool bRequireSight = true);
    static void Heal(AWarCharacter* Target, float Amount, AWarCharacter* Source = nullptr);
private:
    friend class FWarCampaignCombatStateTest;
    double Now() const;
    float Strongest(FName Kind) const;
    UPROPERTY(Replicated) TArray<FWarActiveStatus> Active;
    struct FPeriodicExecution
    {
        TSharedPtr<const FWarAbilityDefinition> Ability;
        FWarAbilityEffect Effect;
        TWeakObjectPtr<AActor> Target;
        float Base=0, Strength=0;
        int32 Level=1;
        bool bBonus=false;
    };
    TMap<FName,FPeriodicExecution> Periodic;
    TMap<FName,TSharedPtr<const FWarAbilityDefinition>> AppliedDefinitions;
    TMap<FName,FString> SourceKeys, TargetKeys;
};
