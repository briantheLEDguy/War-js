#include "WarAbilityConditions.h"
#include "Dom/JsonObject.h"

namespace
{
    FString Str(const TSharedPtr<const FJsonObject>& J, const TCHAR* Key)
    { FString V; if (J) J->TryGetStringField(Key,V); return V; }
    double Num(const TSharedPtr<const FJsonObject>& J, const TCHAR* Key, double Default=0)
    { double V; return J && J->TryGetNumberField(Key,V) ? V : Default; }
    TSharedPtr<FJsonObject> Obj(const TSharedPtr<const FJsonObject>& J, const TCHAR* Key)
    { const TSharedPtr<FJsonObject>* V; return J && J->TryGetObjectField(Key,V) ? *V : nullptr; }
    bool OneOf(FName Value, std::initializer_list<const TCHAR*> Choices)
    { for (const auto* Choice : Choices) if (Value == Choice) return true; return false; }
    bool Check(const FWarAbilityCondition& Node, const FWarConditionContext& C, const FString& Path, TArray<FWarPredicateTrace>& Traces)
    {
        if (Node.Kind == TEXT("all") || Node.Kind == TEXT("any"))
        {
            bool Result = Node.Kind == TEXT("all");
            for (int32 I=0; I<Node.Children.Num(); ++I)
            { const bool Value=Check(Node.Children[I],C,Path+FString::Printf(TEXT(".%d"),I),Traces); Result=Node.Kind==TEXT("all") ? Result && Value : Result || Value; }
            return !Node.Children.IsEmpty() && Result;
        }
        const auto& Subject = Node.Subject == TEXT("caster") ? C.Caster : Node.Subject == TEXT("target") ? C.Target : C.Recipient;
        FWarPredicateTrace Trace; Trace.Path=Path; Trace.SubjectId=Subject.Id;
        bool Found=false;
        if (Subject.bAlive && !Subject.Id.IsNone())
        {
            if (Node.Kind == TEXT("casting")) Found = Subject.CastingAbility==Node.AbilityId && OneOf(Subject.ActionState,{TEXT("casting"),TEXT("channeling")});
            else for (const auto& Status : Subject.Statuses)
            {
                if (Status.Expires<=C.Now || (Status.Category==TEXT("shield") && Status.Remaining<=0)) continue;
                if (Node.Source==TEXT("self") && Status.SourceId!=C.Caster.Id) continue;
                if (Node.Source==TEXT("allied") && (C.Caster.Realm.IsNone() || Status.SourceRealm!=C.Caster.Realm)) continue;
                const bool Match = OneOf(Node.Kind,{TEXT("hot"),TEXT("dot")}) ? Status.Category==Node.Kind
                    : Status.AbilityId==Node.AbilityId && (Node.Kind!=TEXT("effect") || Status.EffectId==Node.EffectId);
                if (Match) { Found=true; Trace.Sources.AddUnique(Status.SourceId); }
            }
        }
        Trace.bPassed=Subject.bAlive && !Subject.Id.IsNone() && (Node.bNot ? !Found : Found);
        Traces.Add(Trace); return Trace.bPassed;
    }
    bool ParseNode(const TSharedPtr<const FJsonObject>& J, FWarAbilityCondition& Out, int32 Depth, int32& Count, FString& Error)
    {
        if (!J) { Error=TEXT("Missing condition."); return false; }
        Out.Kind=FName(*Str(J,TEXT("kind")));
        if (OneOf(Out.Kind,{TEXT("all"),TEXT("any")}))
        {
            const TArray<TSharedPtr<FJsonValue>>* Children;
            if (Depth>2 || !J->TryGetArrayField(TEXT("children"),Children) || Children->IsEmpty() || Children->Num()>16)
            { Error=TEXT("Conditions allow two group levels and 1-16 children."); return false; }
            for (const auto& Value : *Children)
            { FWarAbilityCondition Child; if (!ParseNode(Value->AsObject(),Child,Depth+1,Count,Error)) return false; Out.Children.Add(MoveTemp(Child)); }
            return true;
        }
        Out.Subject=FName(*Str(J,TEXT("subject"))); Out.Source=FName(*Str(J,TEXT("source")));
        Out.AbilityId=FName(*Str(J,TEXT("abilityId"))); Out.EffectId=FName(*Str(J,TEXT("effectId"))); J->TryGetBoolField(TEXT("not"),Out.bNot);
        if (++Count>16 || !OneOf(Out.Kind,{TEXT("ability_effect"),TEXT("effect"),TEXT("hot"),TEXT("dot"),TEXT("casting")})
            || !OneOf(Out.Subject,{TEXT("caster"),TEXT("target"),TEXT("recipient")}) || !OneOf(Out.Source,{TEXT("self"),TEXT("allied"),TEXT("any")}))
        { Error=TEXT("Invalid condition kind, subject, source, or predicate limit."); return false; }
        return true;
    }
}

FWarRuleEvaluation WarAbilityConditions::Evaluate(const TArray<FWarConditionalRule>& Rules, FName Event, const FWarConditionContext& Context)
{
    FWarRuleEvaluation Result;
    for (const auto& Rule : Rules)
    {
        if (Rule.Event!=Event) continue;
        FWarRuleTrace Trace; Trace.RuleId=Rule.Id; Trace.Event=Event; Trace.At=Context.Now; Trace.RecipientId=Context.Recipient.Id;
        Trace.bPassed=Check(Rule.Condition,Context,TEXT("condition"),Trace.Predicates); Result.Traces.Add(Trace);
        if (!Trace.bPassed) continue;
        for (const auto& Action : Rule.Actions)
            if (Action.Kind==TEXT("add_effect")) Result.BonusEffects.Add(Action.Effect);
            else { auto& M=Result.Modifiers.FindOrAdd(Action.EffectId); if (Action.Kind==TEXT("flat")) M.Flat+=Action.Value; else M.Percent+=Action.Value; }
    }
    return Result;
}
float WarAbilityConditions::Amount(float Base, FName EffectId, const TArray<FWarRuleEvaluation>& Evaluations)
{
    float Flat=0, Percent=0;
    for (const auto& Evaluation : Evaluations) if (const auto* M=Evaluation.Modifiers.Find(EffectId)) { Flat+=M->Flat; Percent+=M->Percent; }
    return FMath::Max(0.f,FMath::RoundToFloat((Base+Flat)*(1+Percent)));
}
bool WarAbilityConditions::ParseEffect(const TSharedPtr<const FJsonObject>& J, FWarAbilityEffect& E, FString& Error)
{
    if (!J) { Error=TEXT("Effect must be an object."); return false; }
    E.Id=FName(*Str(J,TEXT("id"))); E.Kind=FName(*Str(J,TEXT("kind"))); E.School=FName(*Str(J,TEXT("school"))); E.Recipient=FName(*Str(J,TEXT("recipient")));
    const auto Amount=Obj(J,TEXT("amount")), Status=Obj(J,E.Kind==TEXT("player_status") ? TEXT("playerStatus") : TEXT("status")), Movement=Obj(J,TEXT("movement")), Periodic=Obj(J,TEXT("periodic"));
    E.Minimum=Num(Amount,TEXT("min")); E.Maximum=Num(Amount,TEXT("max")); E.StatScale=Num(Amount,TEXT("statScale")); E.LevelScale=Num(Amount,TEXT("levelScale")); E.ResourceScale=Num(Amount,TEXT("resourceScale"));
    E.bHasAmount=Amount.IsValid();
    E.StatusId=FName(*Str(Status,TEXT("id"))); E.StatusKind=FName(*Str(Status,TEXT("kind"))); E.Label=Str(Status,TEXT("label"));
    E.Duration=Num(Status,TEXT("durationSec")); E.Magnitude=Num(Status,TEXT("magnitude"),E.StatusKind==TEXT("slow") ? .3 : .15);
    E.Modifier=FName(*Str(Status,TEXT("damageModifier"))); E.StackGroup=FName(*Str(Status,TEXT("stackGroup")));
    E.Direction=FName(*Str(Movement,TEXT("mode"))); E.Distance=Num(Movement,TEXT("distance"))*100;
    E.PeriodicDuration=Num(Periodic,TEXT("durationSec")); E.Interval=Num(Periodic,TEXT("intervalSec"),1);
    const TArray<TSharedPtr<FJsonValue>>* Kinds; const auto Cleanse=Obj(J,TEXT("cleanse"));
    if (Cleanse && Cleanse->TryGetArrayField(TEXT("kinds"),Kinds)) for (const auto& Value : *Kinds) E.Cleanse.Add(FName(*Value->AsString()));
    if (E.Id.IsNone() || !OneOf(E.Kind,{TEXT("damage"),TEXT("heal"),TEXT("status"),TEXT("player_status"),TEXT("movement"),TEXT("cleanse"),TEXT("wrath_relic")})
        || !OneOf(E.Recipient,{TEXT("caster"),TEXT("target"),TEXT("allies"),TEXT("enemies")})) { Error=TEXT("Invalid effect identity, recipient, or kind."); return false; }
    for (float Value : {E.Minimum,E.Maximum,E.StatScale,E.LevelScale,E.ResourceScale,E.Duration,E.Magnitude,E.Distance,E.PeriodicDuration,E.Interval})
        if (!FMath::IsFinite(Value) || Value<0 || Value>1000000) { Error=TEXT("Effect values must be finite and bounded."); return false; }
    if (E.Minimum>E.Maximum || E.Duration>60 || E.Distance>1200 || (Periodic && (!OneOf(E.Kind,{TEXT("damage"),TEXT("heal")}) || E.PeriodicDuration<.1f || E.PeriodicDuration>60 || E.Interval<.1f || E.Interval>E.PeriodicDuration)))
    { Error=TEXT("Invalid effect amount, duration, movement, or periodic interval."); return false; }
    if (OneOf(E.Kind,{TEXT("damage"),TEXT("heal")}) && (!Amount || !Amount->HasTypedField<EJson::Number>(TEXT("min")) || !Amount->HasTypedField<EJson::Number>(TEXT("max"))))
    { Error=TEXT("Damage/healing requires a numeric minimum and maximum."); return false; }
    if (E.StatScale>1000 || E.LevelScale>1000 || E.ResourceScale>1000) { Error=TEXT("Scaling exceeds 1000."); return false; }
    if (OneOf(E.Kind,{TEXT("status"),TEXT("player_status")}))
    {
        const bool Valid=E.Kind==TEXT("status") ? OneOf(E.StatusKind,{TEXT("burn"),TEXT("bleed"),TEXT("slow"),TEXT("root"),TEXT("silence"),TEXT("stagger"),TEXT("mark"),TEXT("debuff")}) : OneOf(E.StatusKind,{TEXT("shield"),TEXT("guard"),TEXT("empower"),TEXT("haste")});
        const float Limit=OneOf(E.StatusKind,{TEXT("root"),TEXT("silence"),TEXT("stagger")}) ? 1 : E.StatusKind==TEXT("guard") ? .75f : .6f;
        if (!Valid || E.Duration<.01f || E.Magnitude>Limit) { Error=TEXT("Invalid status type, duration, or magnitude."); return false; }
    }
    if (E.Kind==TEXT("movement") && (E.Recipient!=TEXT("caster") || !OneOf(E.Direction,{TEXT("forward"),TEXT("backward"),TEXT("toward_target")})))
    { Error=TEXT("Movement requires the caster and a supported direction."); return false; }
    if (E.Kind==TEXT("cleanse"))
    { if (!Cleanse || !Cleanse->HasTypedField<EJson::Array>(TEXT("kinds"))) { Error=TEXT("Cleanse kinds are required."); return false; }
      for (FName Kind:E.Cleanse) if (!OneOf(Kind,{TEXT("slow"),TEXT("root"),TEXT("stagger"),TEXT("debuff")})) { Error=TEXT("Unsupported cleanse kind."); return false; } }
    return true;
}
bool WarAbilityConditions::ParseRules(const TSharedPtr<const FJsonObject>& J, TArray<FWarConditionalRule>& Out, FString& Error)
{
    Out.Reset(); const TArray<TSharedPtr<FJsonValue>>* Rules;
    if (!J || !J->TryGetArrayField(TEXT("conditions"),Rules)) return true;
    if (Rules->Num()>16) { Error=TEXT("At most 16 conditional rules per ability."); return false; }
    TSet<FName> Ids;
    for (const auto& Value : *Rules)
    {
        const auto Row=Value->AsObject(); if (!Row) { Error=TEXT("Invalid conditional rule."); return false; }
        FWarConditionalRule Rule; Rule.Id=FName(*Str(Row,TEXT("id"))); Rule.Event=FName(*Str(Row,TEXT("event"))); Rule.Name=Str(Row,TEXT("name")); int32 Count=0;
        if (Rule.Id.IsNone() || Ids.Contains(Rule.Id) || !OneOf(Rule.Event,{TEXT("cast_start"),TEXT("application"),TEXT("tick")})
            || !ParseNode(Obj(Row,TEXT("condition")),Rule.Condition,1,Count,Error) || !OneOf(Rule.Condition.Kind,{TEXT("all"),TEXT("any")}))
        { if (Error.IsEmpty()) Error=TEXT("Invalid rule identity, event, or root group."); return false; }
        Ids.Add(Rule.Id); const TArray<TSharedPtr<FJsonValue>>* Actions;
        if (!Row->TryGetArrayField(TEXT("actions"),Actions) || Actions->IsEmpty() || Actions->Num()>32) { Error=TEXT("A rule requires 1-32 actions."); return false; }
        for (const auto& Entry : *Actions)
        {
            const auto A=Entry->AsObject(); FWarConditionalAction Action; Action.Kind=FName(*Str(A,TEXT("kind"))); Action.EffectId=FName(*Str(A,TEXT("effectId"))); Action.Value=Num(A,TEXT("value"));
            if (Action.Kind==TEXT("add_effect")) { if (!ParseEffect(Obj(A,TEXT("effect")),Action.Effect,Error)) return false; }
            else if (!OneOf(Action.Kind,{TEXT("flat"),TEXT("percent")}) || !FMath::IsFinite(Action.Value) || FMath::Abs(Action.Value)>1000000
                || (Action.Kind==TEXT("percent") && (Action.Value < -1 || Action.Value > 100))) { Error=TEXT("Invalid conditional amount modifier."); return false; }
            Rule.Actions.Add(MoveTemp(Action));
        }
        Out.Add(MoveTemp(Rule));
    }
    return true;
}
bool WarAbilityConditions::Validate(const FWarAbilityDefinition& Ability, const TArray<FWarAbilityDefinition>& Catalog, FString& Error)
{
    TSet<FName> EffectIds;
    for (const auto& E : Ability.Effects) { if (E.Id.IsNone() || EffectIds.Contains(E.Id)) { Error=TEXT("Duplicate or missing effect identity."); return false; } EffectIds.Add(E.Id); }
    for (const auto& Rule : Ability.Conditions)
    {
        TFunction<bool(const FWarAbilityCondition&)> ValidateNode = [&](const FWarAbilityCondition& Node) {
            for (const auto& Child : Node.Children) if (!ValidateNode(Child)) return false;
            if (Rule.Event==TEXT("cast_start") && Node.Subject==TEXT("recipient"))
            { Error=TEXT("Use caster or selected target at cast start."); return false; }
            if (OneOf(Node.Kind,{TEXT("ability_effect"),TEXT("effect"),TEXT("casting")}))
            {
                const auto* Reference=Catalog.FindByPredicate([&](const auto& A) { return A.Id==Node.AbilityId; });
                const bool HasEffect=Reference && (Reference->Effects.ContainsByPredicate([&](const auto& E) { return E.Id==Node.EffectId; })
                    || Reference->Conditions.ContainsByPredicate([&](const auto& R) { return R.Actions.ContainsByPredicate([&](const auto& Action) { return Action.Kind==TEXT("add_effect") && Action.Effect.Id==Node.EffectId; }); }));
                if (!Reference || (Node.Kind==TEXT("effect") && !HasEffect))
                { Error=TEXT("Conditional ability/effect reference is missing."); return false; }
            }
            return true;
        };
        if (!ValidateNode(Rule.Condition)) return false;
        if (Rule.Event==TEXT("tick") && Ability.TimingMode!=TEXT("channel") && !Ability.Effects.ContainsByPredicate([](const auto& E) { return E.PeriodicDuration>0; }))
        { Error=TEXT("Tick rules require a periodic effect or channel."); return false; }
        TSet<FString> Modifiers;
        for (const auto& Action : Rule.Actions)
        {
            if (Action.Kind==TEXT("add_effect"))
            {
                if (EffectIds.Contains(Action.Effect.Id) || !OneOf(Action.Effect.Kind,{TEXT("damage"),TEXT("heal"),TEXT("status"),TEXT("player_status")})
                    || (Rule.Event==TEXT("tick") && (Action.Effect.PeriodicDuration>0 || OneOf(Action.Effect.StatusKind,{TEXT("burn"),TEXT("bleed")}))))
                { Error=TEXT("Bonus effect identity, kind, or periodic scheduler is invalid."); return false; }
                EffectIds.Add(Action.Effect.Id);
            }
            else
            {
                const auto* Effect=Ability.Effects.FindByPredicate([&](const auto& E) { return E.Id==Action.EffectId; });
                const FString Key=Action.Kind.ToString()+TEXT(":")+Action.EffectId.ToString();
                if (!Effect || !OneOf(Effect->Kind,{TEXT("damage"),TEXT("heal")}) || Modifiers.Contains(Key)
                    || (Rule.Event==TEXT("tick") && Effect->PeriodicDuration<=0 && Ability.TimingMode!=TEXT("channel")))
                { Error=TEXT("Conditional modifier must name one base damage/healing effect."); return false; }
                Modifiers.Add(Key);
            }
        }
    }
    return true;
}
FString WarAbilityConditions::Summary(const FWarAbilityCondition& Node)
{
    if (Node.Kind==TEXT("all") || Node.Kind==TEXT("any"))
    { TArray<FString> Parts; for (const auto& C : Node.Children) Parts.Add(Summary(C)); return TEXT("(")+FString::Join(Parts,Node.Kind==TEXT("all") ? TEXT(" AND ") : TEXT(" OR "))+TEXT(")"); }
    return Node.Subject.ToString()+(Node.bNot ? TEXT(" IS NOT ") : TEXT(" IS "))+Node.Kind.ToString()
        +(Node.AbilityId.IsNone() ? TEXT("") : TEXT(" ")+Node.AbilityId.ToString())+(Node.EffectId.IsNone() ? TEXT("") : TEXT(" / ")+Node.EffectId.ToString())+TEXT(" [")+Node.Source.ToString()+TEXT("]");
}
