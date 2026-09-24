#pragma once
#include "CoreMinimal.h"
#include "WarAbilityCatalog.h"

struct FWarStatusObservation
{
    FName AbilityId, EffectId, SourceId, SourceRealm, Category;
    double Expires = 0;
    float Remaining = 0;
};
struct FWarCombatObservation
{
    FName Id, Realm, CastingAbility, ActionState;
    bool bAlive = false;
    TArray<FWarStatusObservation> Statuses;
};
struct FWarConditionContext
{
    double Now = 0;
    FWarCombatObservation Caster, Target, Recipient;
};
struct FWarPredicateTrace
{
    FString Path;
    FName SubjectId;
    bool bPassed = false;
    TArray<FName> Sources;
};
struct FWarRuleTrace
{
    FName RuleId, Event, RecipientId;
    double At = 0;
    bool bPassed = false;
    TArray<FWarPredicateTrace> Predicates;
};
struct FWarAmountModifier { float Flat = 0, Percent = 0; };
struct FWarRuleEvaluation
{
    TMap<FName, FWarAmountModifier> Modifiers;
    TArray<FWarAbilityEffect> BonusEffects;
    TArray<FWarRuleTrace> Traces;
};

/** Pure predicates over an event snapshot; no effect application or recursive dispatch. */
namespace WarAbilityConditions
{
    AEGISWAR_API FWarRuleEvaluation Evaluate(const TArray<FWarConditionalRule>& Rules, FName Event, const FWarConditionContext& Context);
    AEGISWAR_API float Amount(float Base, FName EffectId, const TArray<FWarRuleEvaluation>& Evaluations);
    AEGISWAR_API bool ParseEffect(const TSharedPtr<const FJsonObject>& Json, FWarAbilityEffect& Out, FString& Error);
    AEGISWAR_API bool ParseRules(const TSharedPtr<const FJsonObject>& Json, TArray<FWarConditionalRule>& Out, FString& Error);
    AEGISWAR_API bool Validate(const FWarAbilityDefinition& Ability, const TArray<FWarAbilityDefinition>& Catalog, FString& Error);
    AEGISWAR_API FString Summary(const FWarAbilityCondition& Condition);
}
