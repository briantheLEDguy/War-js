#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityConditions.h"
#include "WarCharacterVisualDefinition.h"
#include "WarAbilityRuntime.generated.h"
class AWarCharacter;

/** Immutable launch inputs and per-impact evaluation caches, independent of the next action. */
struct FWarAbilityImpact
{
    TSharedPtr<const FWarAbilityDefinition> Definition;
    TWeakObjectPtr<AWarCharacter> Pawn;
    TWeakObjectPtr<AActor> Target;
    FName Zone;
    FVector Origin, Facing, Ground;
    float Spent = 0, Strength = 0;
    int32 Level = 1;
    bool bReleased = false;
    double Arrives = 0;
    FWarRuleEvaluation CastConditions;
    TMap<TWeakObjectPtr<AActor>,FWarRuleEvaluation> ApplicationConditions;
    TMap<FString,float> ChannelBaselines;
};

USTRUCT()
struct FWarAbilityCooldown
{
    GENERATED_BODY()
    UPROPERTY() FName Id;
    UPROPERTY() double Until = 0;
    int64 ExpiresAtUnixMs = 0;
};

/** Client sends only a catalog ID and target; server owns every effect and timing decision. */
UCLASS()
class AEGISWAR_API UWarAbilityRuntime : public UActorComponent
{
    GENERATED_BODY()
public:
    UWarAbilityRuntime();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* Function) override;
    void InitializeCharacter(AWarCharacter* Pawn);
    FName GetCareer() const { return Career; }
    float GetResource() const { return Resource; }
    double Now() const;
    float Cooldown(FName Id) const;
    bool IsBusy() const { return bBasicPending || Now() < BusyUntil; }
    double ReadyIn(FName Id) const;
    bool HasMovementIntent() const { return bMovementIntent; }
    bool IsStationaryCast() const { return bMovementCancelable && !Casting.IsNone(); }
    bool OwnsMovement() const;
    void UpdateMovementIntent(bool bMoving, bool bJump = false);
    UFUNCTION(Server, Reliable) void ServerMovementIntent(bool bMoving, bool bJump);
    bool QueueAbility(FName Id, AActor* Target, const FString& Version, const FVector& Ground);
    uint32 BeginBasicAttack(float ContactSeconds);
    void FinishBasicAttack(uint32 Serial);
    uint32 GetActionSerial() const { return ActionSerial; }
    FName GetCastingAbility() const { return Casting; }
    const FString& GetPublicCastLabel() const { return PublicCastLabel; }
    double GetPublicCastStart() const { return PublicCastStart; }
    double GetPublicCastEnd() const { return PublicCastEnd; }
    bool IsPublicCastInterruptible() const { return PublicCastEnd > Now(); }
    FName GetActionState() const;
    const TArray<FWarRuleTrace>& GetConditionTraces() const { return ConditionTraces; }
    void RecordConditions(const TArray<FWarRuleTrace>& Traces);
    bool CanActivate(const FWarAbilityDefinition& Ability, AActor* Target, FString& Error, bool bCheckMovement = true) const;
    /** Advisory AI preflight ignores current locomotion only; TryActivate always checks actual movement again. */
    bool CanPrepareStationaryCast(const FWarAbilityDefinition& Ability,AActor* Target,FString& Error) const;
    bool TryActivate(FName Id, AActor* Target, FString& Error, const FVector* Ground=nullptr);
    UFUNCTION(Server, Reliable) void ServerActivate(FName Id, AActor* Target);
    UFUNCTION(Server, Reliable) void ServerActivateVersioned(FName Id, AActor* Target, const FString& Version, FVector Ground);
    UFUNCTION(Client, Reliable) void ClientResult(const FString& Message);
    UFUNCTION(Client, Reliable) void ClientCatalogChunk(const FString& Version,int32 Index,int32 Count,const FString& Chunk);
    FString Description() const;
    FString GetMessage() const { return Now() < MessageUntil ? LastMessage : FString(); }
    void RestoreResource();
    void ResetCooldowns();
    TSharedPtr<class FJsonObject> CaptureScenarioState() const;
    void RestoreScenarioState(const TSharedPtr<class FJsonObject>& State);
    TSharedPtr<class FJsonObject> CaptureCampaignState(int64 CapturedAt) const;
    bool RestoreCampaignState(const TSharedPtr<class FJsonObject>& State,int64 CapturedAt,int64 CurrentUtc,FString& Error,bool Apply=true);
    void Interrupt();
private:
    friend class FWarAbilityPreparationTest;
    bool CheckActivation(const FWarAbilityDefinition& Ability,AActor* Target,FString& Error,bool bCheckMovement,bool bCheckMovementIntent) const;
    UWarAbilityCatalog* Catalog() const;
    AWarCharacter* Avatar() const;
    bool MovementDestination(const FWarAbilityDefinition& Ability, AActor* Target, FVector& End, FString& Error, TArray<FVector>* OutPath = nullptr) const;
    void BeginMotion(const FWarAbilityDefinition& Ability);
    void Resolve(const FWarAbilityDefinition& Ability);
    void ResolveImpact(FWarAbilityImpact& Impact);
    FWarAbilityImpact CaptureImpact() const;
    void Cancel(bool bMovement = false, bool bStopPresentation = true);
    void ProcessQueue();
    void PublishCast(const FWarAbilityDefinition& Ability);
    UPROPERTY(Replicated) FString PublicCastLabel;
    UPROPERTY(Replicated) double PublicCastStart = 0;
    UPROPERTY(Replicated) double PublicCastEnd = 0;
    UPROPERTY(Replicated) FName Career;
    UPROPERTY(Replicated) float Resource = 0;
    UPROPERTY(Replicated) double GcdUntil = 0;
    int64 GcdExpiresAtUnixMs = 0;
    UPROPERTY(Replicated) double BusyUntil = 0;
    UPROPERTY(Replicated) bool bMovementCancelable = false;
    UPROPERTY(Replicated) bool bTravelActive = false;
    UPROPERTY(Replicated) TArray<FWarAbilityCooldown> Cooldowns;
    UPROPERTY(Replicated) FName Casting;
    TWeakObjectPtr<AWarCharacter> PendingPawn;
    TWeakObjectPtr<AActor> PendingTarget;
    FName PendingZone;
    FVector Origin = FVector::ZeroVector, Facing = FVector::ForwardVector, MoveStart = FVector::ZeroVector, MoveEnd = FVector::ZeroVector;
    TArray<FVector> MovePath;
    double ReleaseAt = 0, MoveAt = 0, MoveUntil = 0, NextRequest = 0, MessageUntil = 0;
    float Spent = 0, Strength = 0;
    int32 Level = 1;
    bool bReleased = false;
    bool bMotionDuringTravel = false;
    bool bMovementIntent = false, bEffectCommitted = false;
    bool bBasicPending = false;
    float ResourceDelta = 0, ManaPaid = 0;
    uint32 ActionSerial = 0;
    TArray<FWarAbilityImpact> Projectiles;
    FName QueuedAbility;
    TWeakObjectPtr<AActor> QueuedTarget;
    TWeakObjectPtr<AWarCharacter> QueuedPawn;
    FName QueuedZone;
    FString QueuedVersion;
    FVector QueuedGround = FVector::ZeroVector;
    double QueueExpires = 0;
    TSharedPtr<const FWarAbilityDefinition> Activation;
    TOptional<FWarAbilityPresentation> ActivationPresentation;
    FWarRuleEvaluation CastConditions;
    TMap<TWeakObjectPtr<AActor>,FWarRuleEvaluation> ApplicationConditions;
    TMap<FString,float> ChannelBaselines;
    TArray<FWarRuleTrace> ConditionTraces;
    FVector GroundPoint=FVector::ZeroVector;
    double ChannelUntil=0, NextChannelTick=0;
    FString LastMessage;
    FString SentCatalogVersion=TEXT("baseline"),SendingCatalogVersion,ReceivingCatalogVersion,ReceivingCatalog;
    TArray<FString> SendingCatalog;
    int32 SendingIndex=0,ReceivingIndex=0,ReceivingCount=0;
    double NextCatalogChunk=0;
    void SynchronizeCatalog();
};
