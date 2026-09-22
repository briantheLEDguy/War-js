#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "WarAbilityCatalog.generated.h"

class FJsonObject;

struct FWarAbilityEffect
{
    FName Kind, School, StatusId, StatusKind, Modifier, StackGroup, Direction;
    FString Label;
    float Minimum = 0, Maximum = 0, StatScale = 0, LevelScale = 0, ResourceScale = 0;
    float Duration = 0, Magnitude = 0, Distance = 0;
    TArray<FName> Cleanse;
};

struct FWarAbilityDefinition
{
    FName Id, Career, Shape, School;
    FString Name, Summary, UnavailableReason, ResourceLabel;
    int32 Slot = 0, UnlockLevel = 1;
    bool bEnemyTarget = false, bSpendAll = false, bBlockedBySilence = false;
    float Range = 0, Radius = 0, ProjectileSpeed = 0, Cooldown = 0, Gcd = 0;
    float Mana = 0, Build = 0, Cost = 0, MinimumResource = 0, ResourceMax = 100, ResourceInitial = 0;
    float ReleaseFraction = .4f;
    TArray<FWarAbilityEffect> Effects;
};

namespace WarAbilities
{
    AEGISWAR_API bool Parse(const TSharedPtr<const FJsonObject>& Manifest, TArray<FWarAbilityDefinition>& Out, FString& Error);
    AEGISWAR_API FName Motion(const FWarAbilityDefinition& Ability, FName Profile);
    AEGISWAR_API float ReleaseFraction(const FWarAbilityDefinition& Ability, FName Profile);
    AEGISWAR_API float Amount(const FWarAbilityEffect& Effect, float Strength, int32 Level, float Spent, float Random);
    AEGISWAR_API float ResourceAfter(const FWarAbilityDefinition& Ability, float Current);
}

/** One validated copy of the exported class kits, shared by server gameplay and local UI. */
UCLASS()
class AEGISWAR_API UWarAbilityCatalog : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    const FWarAbilityDefinition* Find(FName Id) const;
    TArray<const FWarAbilityDefinition*> Kit(FName Career) const;
    const FString& GetError() const { return Error; }
private:
    TArray<FWarAbilityDefinition> Definitions;
    FString Error;
};
