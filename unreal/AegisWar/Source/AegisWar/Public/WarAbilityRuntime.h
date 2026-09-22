#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityRuntime.generated.h"
class AWarCharacter;

USTRUCT()
struct FWarAbilityCooldown
{
    GENERATED_BODY()
    UPROPERTY() FName Id;
    UPROPERTY() double Until = 0;
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
    bool IsBusy() const { return Now() < BusyUntil; }
    bool CanActivate(const FWarAbilityDefinition& Ability, AActor* Target, FString& Error, bool bCheckMovement = true) const;
    bool TryActivate(FName Id, AActor* Target, FString& Error);
    UFUNCTION(Server, Reliable) void ServerActivate(FName Id, AActor* Target);
    UFUNCTION(Client, Reliable) void ClientResult(const FString& Message);
    FString Description() const;
    FString GetMessage() const { return Now() < MessageUntil ? LastMessage : FString(); }
    void RestoreResource();
    void ResetCooldowns();
private:
    UWarAbilityCatalog* Catalog() const;
    AWarCharacter* Avatar() const;
    bool MovementDestination(const FWarAbilityDefinition& Ability, AActor* Target, FVector& End, FString& Error, TArray<FVector>* OutPath = nullptr) const;
    void BeginMotion(const FWarAbilityDefinition& Ability);
    void Resolve(const FWarAbilityDefinition& Ability);
    void Cancel();
    UPROPERTY(Replicated) FName Career;
    UPROPERTY(Replicated) float Resource = 0;
    UPROPERTY(Replicated) double GcdUntil = 0;
    UPROPERTY(Replicated) double BusyUntil = 0;
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
    FString LastMessage;
};
