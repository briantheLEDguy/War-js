#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "WarAbilityCatalog.generated.h"

class FJsonObject;

struct FWarAbilityEffect
{
    FName Id, Recipient;
    FName Kind, School, StatusId, StatusKind, Modifier, StackGroup, Direction;
    FString Label;
    float Minimum = 0, Maximum = 0, StatScale = 0, LevelScale = 0, ResourceScale = 0;
    float Duration = 0, Magnitude = 0, Distance = 0;
    float PeriodicDuration = 0, Interval = 1;
    bool bHasAmount = false;
    TArray<FName> Cleanse;
};

struct FWarAbilityCondition
{
    FName Kind, Subject, Source, AbilityId, EffectId;
    bool bNot = false;
    TArray<FWarAbilityCondition> Children;
};
struct FWarConditionalAction
{
    FName Kind, EffectId;
    float Value = 0;
    FWarAbilityEffect Effect;
};
struct FWarConditionalRule
{
    FName Id, Event;
    FString Name;
    FWarAbilityCondition Condition;
    TArray<FWarConditionalAction> Actions;
};

struct FWarAbilityDefinition
{
    FName Id, Career, Shape, School, AssignmentId, TargetKind, TimingMode;
    FString Version;
    TMap<FName, FName> Presentations;
    FString Name, Summary, UnavailableReason, ResourceLabel;
    int32 Slot = 0, UnlockLevel = 1;
    bool bEnemyTarget = false, bSpendAll = false, bBlockedBySilence = false;
    bool bLegacyTargeting = true;
    bool bAuthoredTiming = false;
    float Range = 0, Radius = 0, ProjectileSpeed = 0, Cooldown = 0, Gcd = 0;
    float Mana = 0, Build = 0, Cost = 0, MinimumResource = 0, ResourceMax = 100, ResourceInitial = 0;
    float ReleaseFraction = .4f;
    float CastSeconds = 0, ChannelSeconds = 0, TickInterval = 1;
    int32 MaxTargets = 128;
    TArray<FWarAbilityEffect> Effects;
    TArray<FWarConditionalRule> Conditions;
};

namespace WarAbilities
{
    AEGISWAR_API bool Parse(const TSharedPtr<const FJsonObject>& Manifest, TArray<FWarAbilityDefinition>& Out, FString& Error,bool bAllowEmpty=false);
    AEGISWAR_API FName Motion(const FWarAbilityDefinition& Ability, FName Profile);
    AEGISWAR_API float ReleaseFraction(const FWarAbilityDefinition& Ability, FName Profile);
    AEGISWAR_API float Amount(const FWarAbilityEffect& Effect, float Strength, int32 Level, float Spent, float Random);
    AEGISWAR_API float RawAmount(const FWarAbilityEffect& Effect, float Strength, int32 Level, float Spent, float Random);
    AEGISWAR_API float ResourceAfter(const FWarAbilityDefinition& Ability, float Current);
}

/** One validated copy of the exported class kits, shared by server gameplay and local UI. */
UCLASS()
class AEGISWAR_API UWarAbilityCatalog : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    const FWarAbilityDefinition* Find(FName Id, FName Career = NAME_None) const;
    TArray<const FWarAbilityDefinition*> Kit(FName Career) const;
    const FString& GetError() const { return Error; }
    const TArray<FWarAbilityDefinition>& All() const { return Definitions; }
    const FString& GetVersion() const { return Version; }
    const FString& GetActiveDocument() const { return ActiveDocument; }
    /** Staging is complete validation; activation happens only at this world's next tick boundary. */
    bool StageWorkspace(const FString& Json,const FString& InVersion,FString& OutError);
    bool HasStagedVersion() const { return !StagedVersion.IsEmpty(); }
    void CancelStaged(const FString& InVersion);
    /** Trusted caller must authorize and validate presentation admission before committing. */
    bool Install(const TArray<FWarAbilityDefinition>& Candidate, const FString& InVersion, FString& OutError,const TArray<FWarAbilityDefinition>* Library=nullptr);
private:
    TArray<FWarAbilityDefinition> Definitions;
    FString Error;
    FString Version = TEXT("baseline");
    FString ActiveDocument,StagedDocument,StagedVersion;
    TArray<FWarAbilityDefinition> StagedDefinitions,StagedLibrary;
    FDelegateHandle TickBoundary;
    void ActivateStaged(UWorld* World,ELevelTick Tick,float Delta);
};
