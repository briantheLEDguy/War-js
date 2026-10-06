#include "WarCampaignCombatDefinition.h"
#include "WarAbilityConditions.h"
#include "WarCitadelSiegeProof.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

// Value-field lists are shared by the writer, exact schema check and reader.
// No reflected object, current catalog or defaulting parser owns these values.
#define DEFINITION_NAMES(X) X(Id,"id") X(Career,"career") X(Shape,"shape") X(School,"school") X(AssignmentId,"assignmentId") X(TargetKind,"targetKind") X(TimingMode,"timingMode")
#define DEFINITION_STRINGS(X) X(Version,"version",160) X(Name,"name",512) X(Summary,"summary",4096) X(UnavailableReason,"unavailableReason",4096) X(ResourceLabel,"resourceLabel",512)
#define DEFINITION_NUMBERS(X) X(PreparationScale,"preparationScale") X(Range,"range") X(Radius,"radius") X(ProjectileSpeed,"projectileSpeed") X(Cooldown,"cooldown") X(Gcd,"gcd") X(Mana,"mana") X(Build,"build") X(Cost,"cost") X(MinimumResource,"minimumResource") X(ResourceMax,"resourceMax") X(ResourceInitial,"resourceInitial") X(ReleaseFraction,"releaseFraction") X(CastSeconds,"castSeconds") X(ChannelSeconds,"channelSeconds") X(TickInterval,"tickInterval")
#define DEFINITION_BOOLEANS(X) X(bEnemyTarget,"enemyTarget") X(bSpendAll,"spendAll") X(bBlockedBySilence,"blockedBySilence") X(bLegacyTargeting,"legacyTargeting") X(bAuthoredTiming,"authoredTiming") X(bCancelOnMovement,"cancelOnMovement")
#define EFFECT_NAMES(X) X(Id,"id") X(Recipient,"recipient") X(Kind,"kind") X(School,"school") X(StatusId,"statusId") X(StatusKind,"statusKind") X(Modifier,"modifier") X(StackGroup,"stackGroup") X(Direction,"direction")
#define EFFECT_NUMBERS(X) X(Minimum,"minimum") X(Maximum,"maximum") X(StatScale,"statScale") X(LevelScale,"levelScale") X(ResourceScale,"resourceScale") X(Duration,"duration") X(Magnitude,"magnitude") X(Distance,"distance") X(PeriodicDuration,"periodicDuration") X(Interval,"interval")
#define CONDITION_NAMES(X) X(Kind,"kind") X(Subject,"subject") X(Source,"source") X(AbilityId,"abilityId") X(EffectId,"effectId")

namespace
{
    using FObject = TSharedPtr<FJsonObject>;
    bool Fail(FString& Error, const FString& Why)
    { Error = TEXT("Applied combat definition recovery: ") + Why; return false; }
    FString Name(FName Value) { return Value.IsNone() ? FString() : Value.ToString(); }
    bool Identifier(const FString& Value, bool Empty = true)
    {
        if (Value.Len() > 160 || (!Empty && Value.IsEmpty()) || Value == TEXT("__proto__")
            || Value == TEXT("prototype") || Value == TEXT("constructor")) return false;
        for (const TCHAR C : Value)
            if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9')
                || C == '_' || C == '.' || C == ':' || C == '-')) return false;
        return true;
    }
    bool Exact(const FObject& Object, const TArray<FString>& Required, FString& Error)
    {
        if (!Object || Object->Values.Num() != Required.Num()) return Fail(Error, TEXT("Unknown or missing pure value fields."));
        for (const FString& Key : Required) if (!Object->HasField(Key)) return Fail(Error, TEXT("Missing field: ") + Key);
        return true;
    }
    bool ReadString(const FObject& Object, const TCHAR* Key, FString& Out, int32 Limit, FString& Error)
    {
        if (!Object->HasTypedField<EJson::String>(Key) || !Object->TryGetStringField(Key, Out) || Out.Len() > Limit) return Fail(Error, FString(TEXT("Invalid string: ")) + Key);
        for (const TCHAR C : Out)
            if ((C < 32 && C != '\n' && C != '\r' && C != '\t') || C == 127) return Fail(Error, TEXT("Invalid text control value."));
        return true;
    }
    bool ReadName(const FObject& Object, const TCHAR* Key, FName& Out, FString& Error)
    {
        FString Value;
        if (!ReadString(Object, Key, Value, 160, Error) || !Identifier(Value)) return Fail(Error, FString(TEXT("Invalid native identity: ")) + Key);
        Out = Value.IsEmpty() ? NAME_None : FName(*Value); return true;
    }
    bool ReadNumber(const FObject& Object, const TCHAR* Key, float& Out, FString& Error, float Minimum = 0, float Maximum = 1000000)
    {
        double Value;
        if (!Object->HasTypedField<EJson::Number>(Key) || !Object->TryGetNumberField(Key, Value) || !FMath::IsFinite(Value) || Value < Minimum || Value > Maximum)
            return Fail(Error, FString(TEXT("Invalid finite numeric value: ")) + Key);
        Out = static_cast<float>(Value); return true;
    }
    bool ReadInteger(const FObject& Object, const TCHAR* Key, int32& Out, int32 Minimum, int32 Maximum, FString& Error)
    {
        double Value;
        if (!Object->HasTypedField<EJson::Number>(Key) || !Object->TryGetNumberField(Key, Value) || !FMath::IsFinite(Value) || Value < Minimum || Value > Maximum || FMath::FloorToDouble(Value) != Value)
            return Fail(Error, FString(TEXT("Invalid integral value: ")) + Key);
        Out = static_cast<int32>(Value); return true;
    }
    bool ReadBool(const FObject& Object, const TCHAR* Key, bool& Out, FString& Error)
    { return (Object->HasTypedField<EJson::Boolean>(Key) && Object->TryGetBoolField(Key, Out)) || Fail(Error, FString(TEXT("Invalid boolean: ")) + Key); }
    bool ReadArray(const FObject& Object, const TCHAR* Key, const TArray<TSharedPtr<FJsonValue>>*& Out, int32 Limit, FString& Error)
    { return (Object->TryGetArrayField(Key, Out) && Out->Num() <= Limit) || Fail(Error, FString(TEXT("Invalid bounded array: ")) + Key); }
    FObject Child(const FObject& Object, const TCHAR* Key)
    { const FObject* Value; return Object && Object->TryGetObjectField(Key, Value) ? *Value : nullptr; }
    FObject ValueObject(const TSharedPtr<FJsonValue>& Value)
    { return Value && Value->Type==EJson::Object ? Value->AsObject() : nullptr; }
    bool OneOf(FName Value, std::initializer_list<const TCHAR*> Choices)
    { for (const TCHAR* Choice : Choices) if (Value == FName(Choice)) return true; return false; }

    FObject WriteEffect(const FWarAbilityEffect& E)
    {
        auto Row = MakeShared<FJsonObject>();
#define WRITE_NAME(Member,Key) Row->SetStringField(TEXT(Key),Name(E.Member));
        EFFECT_NAMES(WRITE_NAME)
#undef WRITE_NAME
#define WRITE_NUMBER(Member,Key) Row->SetNumberField(TEXT(Key),E.Member);
        EFFECT_NUMBERS(WRITE_NUMBER)
#undef WRITE_NUMBER
        Row->SetStringField(TEXT("label"),E.Label); Row->SetBoolField(TEXT("hasAmount"),E.bHasAmount);
        TArray<TSharedPtr<FJsonValue>> Cleanse;
        for (FName Kind : E.Cleanse) Cleanse.Add(MakeShared<FJsonValueString>(Name(Kind)));
        Row->SetArrayField(TEXT("cleanse"),Cleanse); return Row;
    }
    bool ReadEffect(const FObject& Row, FWarAbilityEffect& E, bool Legacy, bool Default, FString& Error)
    {
        TArray<FString> Required{TEXT("label"),TEXT("hasAmount"),TEXT("cleanse")};
#define KEY(Member,Field) Required.Add(TEXT(Field));
        EFFECT_NAMES(KEY) EFFECT_NUMBERS(KEY)
#undef KEY
        if (!Exact(Row,Required,Error)) return false;
#define READ_NAME(Member,Key) if (!ReadName(Row,TEXT(Key),E.Member,Error)) return false;
        EFFECT_NAMES(READ_NAME)
#undef READ_NAME
#define READ_NUMBER(Member,Key) if (!ReadNumber(Row,TEXT(Key),E.Member,Error)) return false;
        EFFECT_NUMBERS(READ_NUMBER)
#undef READ_NUMBER
        const TArray<TSharedPtr<FJsonValue>>* Cleanse;
        if (!ReadString(Row,TEXT("label"),E.Label,512,Error) || !ReadBool(Row,TEXT("hasAmount"),E.bHasAmount,Error)
            || !ReadArray(Row,TEXT("cleanse"),Cleanse,32,Error)) return false;
        for (const auto& Value : *Cleanse)
        { FString Kind; if (Value->Type!=EJson::String || !Value->TryGetString(Kind) || !Identifier(Kind,false)) return Fail(Error,TEXT("Invalid cleanse identity.")); E.Cleanse.Add(FName(*Kind)); }
        if (Default)
        {
            const FWarAbilityEffect Empty;
            // Modifier actions store the exact default value object, never an opaque bonus effect.
            const auto Wanted = WriteEffect(Empty);
            if (!FJsonValue::CompareEqual(FJsonValueObject(Row),FJsonValueObject(Wanted)))
                return Fail(Error,TEXT("A modifier contains a nondefault bonus effect."));
            return true;
        }
        if (E.Id.IsNone() || E.Kind.IsNone() || (!Legacy && E.Recipient.IsNone())) return Fail(Error,TEXT("Applied effect lacks immutable identity or recipient."));
        // Probe the established parser's semantic rules. A legacy empty recipient
        // stays empty in E; this validation-only recipient does not rewrite it.
        auto Probe = MakeShared<FJsonObject>();
        Probe->SetStringField(TEXT("id"),Name(E.Id)); Probe->SetStringField(TEXT("kind"),Name(E.Kind));
        Probe->SetStringField(TEXT("school"),Name(E.School)); Probe->SetStringField(TEXT("recipient"),E.Recipient.IsNone() ? TEXT("caster") : Name(E.Recipient));
        if (E.bHasAmount)
        {
            auto Amount = MakeShared<FJsonObject>(); Amount->SetNumberField(TEXT("min"),E.Minimum); Amount->SetNumberField(TEXT("max"),E.Maximum);
            Amount->SetNumberField(TEXT("statScale"),E.StatScale); Amount->SetNumberField(TEXT("levelScale"),E.LevelScale); Amount->SetNumberField(TEXT("resourceScale"),E.ResourceScale);
            Probe->SetObjectField(TEXT("amount"),Amount);
        }
        if (!E.StatusKind.IsNone())
        {
            auto Status = MakeShared<FJsonObject>(); Status->SetStringField(TEXT("id"),Name(E.StatusId)); Status->SetStringField(TEXT("kind"),Name(E.StatusKind));
            Status->SetStringField(TEXT("label"),E.Label); Status->SetNumberField(TEXT("durationSec"),E.Duration); Status->SetNumberField(TEXT("magnitude"),E.Magnitude);
            Status->SetStringField(TEXT("damageModifier"),Name(E.Modifier)); Status->SetStringField(TEXT("stackGroup"),Name(E.StackGroup));
            Probe->SetObjectField(E.Kind == TEXT("player_status") ? TEXT("playerStatus") : TEXT("status"),Status);
        }
        auto Movement = MakeShared<FJsonObject>(); Movement->SetStringField(TEXT("mode"),Name(E.Direction)); Movement->SetNumberField(TEXT("distance"),E.Distance / 100.);
        Probe->SetObjectField(TEXT("movement"),Movement);
        if (E.PeriodicDuration > 0)
        { auto Periodic = MakeShared<FJsonObject>(); Periodic->SetNumberField(TEXT("durationSec"),E.PeriodicDuration); Periodic->SetNumberField(TEXT("intervalSec"),E.Interval); Probe->SetObjectField(TEXT("periodic"),Periodic); }
        auto CleanseObject = MakeShared<FJsonObject>(); CleanseObject->SetArrayField(TEXT("kinds"),*Cleanse); Probe->SetObjectField(TEXT("cleanse"),CleanseObject);
        FWarAbilityEffect Validated;
        if (!WarAbilityConditions::ParseEffect(Probe,Validated,Error)) return false;
        if (E.Minimum > E.Maximum || E.Duration > 60 || E.PeriodicDuration > 60 || E.Interval < .1f || E.Distance > 1200)
            return Fail(Error,TEXT("Applied effect duration, amount or interval is invalid."));
        return true;
    }
    FObject WriteCondition(const FWarAbilityCondition& C, int32 Depth, int32& Leaves, FString& Error)
    {
        const bool Group = C.Kind == TEXT("all") || C.Kind == TEXT("any");
        if (Depth > 3 || C.Children.Num() > 16 || (Group && Depth > 2) || (!Group && ++Leaves > 16))
        { Fail(Error,TEXT("Condition depth or predicate budget exceeded.")); return nullptr; }
        auto Row = MakeShared<FJsonObject>();
#define WRITE_NAME(Member,Key) Row->SetStringField(TEXT(Key),Name(C.Member));
        CONDITION_NAMES(WRITE_NAME)
#undef WRITE_NAME
        Row->SetBoolField(TEXT("not"),C.bNot); TArray<TSharedPtr<FJsonValue>> Children;
        for (const auto& Value : C.Children)
        { auto ChildRow = WriteCondition(Value,Depth+1,Leaves,Error); if (!ChildRow) return nullptr; Children.Add(MakeShared<FJsonValueObject>(ChildRow)); }
        Row->SetArrayField(TEXT("children"),Children); return Row;
    }
    bool ReadCondition(const FObject& Row, FWarAbilityCondition& C, int32 Depth, int32& Leaves, FString& Error)
    {
        TArray<FString> Required{TEXT("not"),TEXT("children")};
#define KEY(Member,Field) Required.Add(TEXT(Field));
        CONDITION_NAMES(KEY)
#undef KEY
        if (!Exact(Row,Required,Error)) return false;
#define READ_NAME(Member,Key) if (!ReadName(Row,TEXT(Key),C.Member,Error)) return false;
        CONDITION_NAMES(READ_NAME)
#undef READ_NAME
        const TArray<TSharedPtr<FJsonValue>>* Children;
        if (!ReadBool(Row,TEXT("not"),C.bNot,Error) || !ReadArray(Row,TEXT("children"),Children,16,Error)) return false;
        const bool Group = C.Kind == TEXT("all") || C.Kind == TEXT("any");
        if ((Group && (Depth > 2 || Children->IsEmpty())) || (!Group && (!Children->IsEmpty() || ++Leaves > 16
            || !OneOf(C.Kind,{TEXT("ability_effect"),TEXT("effect"),TEXT("hot"),TEXT("dot"),TEXT("casting")})
            || !OneOf(C.Subject,{TEXT("caster"),TEXT("target"),TEXT("recipient")}) || !OneOf(C.Source,{TEXT("self"),TEXT("allied"),TEXT("any")}))))
            return Fail(Error,TEXT("Invalid pure condition semantics."));
        for (const auto& Value : *Children)
        { FWarAbilityCondition ChildValue; if (!ReadCondition(ValueObject(Value),ChildValue,Depth+1,Leaves,Error)) return false; C.Children.Add(MoveTemp(ChildValue)); }
        return true;
    }
    FObject WriteDefinition(const FWarAbilityDefinition& A, FString& Error)
    {
        if (A.Effects.Num() > 128 || A.Conditions.Num() > 16 || A.Presentations.Num() > 128) { Fail(Error,TEXT("Definition array budget exceeded.")); return nullptr; }
        auto Row = MakeShared<FJsonObject>(); Row->SetNumberField(TEXT("schemaVersion"),1); Row->SetStringField(TEXT("units"),TEXT("native_cm_seconds"));
#define WRITE_NAME(Member,Key) Row->SetStringField(TEXT(Key),Name(A.Member));
        DEFINITION_NAMES(WRITE_NAME)
#undef WRITE_NAME
#define WRITE_STRING(Member,Key,Limit) Row->SetStringField(TEXT(Key),A.Member);
        DEFINITION_STRINGS(WRITE_STRING)
#undef WRITE_STRING
#define WRITE_NUMBER(Member,Key) Row->SetNumberField(TEXT(Key),A.Member);
        DEFINITION_NUMBERS(WRITE_NUMBER)
#undef WRITE_NUMBER
#define WRITE_BOOL(Member,Key) Row->SetBoolField(TEXT(Key),A.Member);
        DEFINITION_BOOLEANS(WRITE_BOOL)
#undef WRITE_BOOL
        Row->SetNumberField(TEXT("slot"),A.Slot); Row->SetNumberField(TEXT("unlockLevel"),A.UnlockLevel); Row->SetNumberField(TEXT("maxTargets"),A.MaxTargets);
        auto Presentations = MakeShared<FJsonObject>(); TArray<FString> Profiles;
        for (const auto& Pair : A.Presentations) Profiles.Add(Name(Pair.Key)); Profiles.Sort();
        for (const FString& Profile : Profiles) Presentations->SetStringField(Profile,Name(A.Presentations.FindChecked(FName(*Profile))));
        Row->SetObjectField(TEXT("presentations"),Presentations);
        TArray<TSharedPtr<FJsonValue>> Effects,Conditions;
        for (const auto& E : A.Effects) { if (E.Cleanse.Num() > 32) { Fail(Error,TEXT("Effect cleanse budget exceeded.")); return nullptr; } Effects.Add(MakeShared<FJsonValueObject>(WriteEffect(E))); }
        for (const auto& Rule : A.Conditions)
        {
            if (Rule.Actions.Num() > 32) { Fail(Error,TEXT("Rule action budget exceeded.")); return nullptr; }
            auto R = MakeShared<FJsonObject>(); R->SetStringField(TEXT("id"),Name(Rule.Id)); R->SetStringField(TEXT("event"),Name(Rule.Event)); R->SetStringField(TEXT("name"),Rule.Name);
            int32 Leaves = 0; auto Condition = WriteCondition(Rule.Condition,1,Leaves,Error); if (!Condition) return nullptr;
            R->SetObjectField(TEXT("condition"),Condition); TArray<TSharedPtr<FJsonValue>> Actions;
            for (const auto& Action : Rule.Actions)
            {
                if (Action.Effect.Cleanse.Num() > 32) { Fail(Error,TEXT("Bonus cleanse budget exceeded.")); return nullptr; }
                auto Item = MakeShared<FJsonObject>(); Item->SetStringField(TEXT("kind"),Name(Action.Kind)); Item->SetStringField(TEXT("effectId"),Name(Action.EffectId));
                Item->SetNumberField(TEXT("value"),Action.Value); Item->SetObjectField(TEXT("effect"),WriteEffect(Action.Effect)); Actions.Add(MakeShared<FJsonValueObject>(Item));
            }
            R->SetArrayField(TEXT("actions"),Actions); Conditions.Add(MakeShared<FJsonValueObject>(R));
        }
        Row->SetArrayField(TEXT("effects"),Effects); Row->SetArrayField(TEXT("conditions"),Conditions); return Row;
    }
}

bool WarCampaignCombatDefinition::Decode(const FString& Payload, const FString& Sha256, FWarAbilityDefinition& Out, FString& Error)
{
    Error.Reset(); const FTCHARToUTF8 Utf8(*Payload); FString Actual;
    if (Utf8.Length() > 65536 || Sha256.Len() != 64 || Sha256 != Sha256.ToLower()
        || !WarCitadelProofHash::Text(Payload,Actual,Error) || Actual != Sha256)
        return Fail(Error,TEXT("Exact immutable UTF-8 payload hash is unavailable or differs."));
    FObject Row; if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Payload),Row) || !Row) return Fail(Error,TEXT("Invalid pure definition JSON."));
    TArray<FString> Required{TEXT("schemaVersion"),TEXT("units"),TEXT("slot"),TEXT("unlockLevel"),TEXT("maxTargets"),TEXT("presentations"),TEXT("effects"),TEXT("conditions")};
#define KEY(Member,Field) Required.Add(TEXT(Field));
    DEFINITION_NAMES(KEY) DEFINITION_NUMBERS(KEY) DEFINITION_BOOLEANS(KEY)
#undef KEY
#define STRING_KEY(Member,Field,Limit) Required.Add(TEXT(Field));
    DEFINITION_STRINGS(STRING_KEY)
#undef STRING_KEY
    if (!Exact(Row,Required,Error)) return false;
    double Schema; FString Units;
    if (!Row->HasTypedField<EJson::Number>(TEXT("schemaVersion")) || !Row->TryGetNumberField(TEXT("schemaVersion"),Schema) || Schema != 1
        || !ReadString(Row,TEXT("units"),Units,32,Error) || Units != TEXT("native_cm_seconds"))
        return Fail(Error,TEXT("Unknown definition schema or units."));
    FWarAbilityDefinition A;
#define READ_NAME(Member,Key) if (!ReadName(Row,TEXT(Key),A.Member,Error)) return false;
    DEFINITION_NAMES(READ_NAME)
#undef READ_NAME
#define READ_STRING(Member,Key,Limit) if (!ReadString(Row,TEXT(Key),A.Member,Limit,Error)) return false;
    DEFINITION_STRINGS(READ_STRING)
#undef READ_STRING
#define READ_NUMBER(Member,Key) if (!ReadNumber(Row,TEXT(Key),A.Member,Error)) return false;
    DEFINITION_NUMBERS(READ_NUMBER)
#undef READ_NUMBER
#define READ_BOOL(Member,Key) if (!ReadBool(Row,TEXT(Key),A.Member,Error)) return false;
    DEFINITION_BOOLEANS(READ_BOOL)
#undef READ_BOOL
    if (A.Id.IsNone() || A.Career.IsNone() || !Identifier(A.Version,false)
        || !ReadInteger(Row,TEXT("slot"),A.Slot,0,1024,Error) || !ReadInteger(Row,TEXT("unlockLevel"),A.UnlockLevel,1,1000,Error)
        || !ReadInteger(Row,TEXT("maxTargets"),A.MaxTargets,1,128,Error)) return Fail(Error,TEXT("Definition identity or integer bounds are invalid."));
    const auto Presentations = Child(Row,TEXT("presentations"));
    if (!Presentations || Presentations->Values.Num() > 128) return Fail(Error,TEXT("Missing bounded pure presentations."));
    for (const auto& Pair : Presentations->Values)
    { const FString Profile(*Pair.Key); FString Motion; if (!Identifier(Profile,false) || Pair.Value->Type!=EJson::String || !Pair.Value->TryGetString(Motion) || !Identifier(Motion,false)) return Fail(Error,TEXT("Invalid native presentation identity.")); A.Presentations.Add(FName(*Profile),FName(*Motion)); }
    const TArray<TSharedPtr<FJsonValue>> *Effects,*Conditions;
    if (!ReadArray(Row,TEXT("effects"),Effects,128,Error) || !ReadArray(Row,TEXT("conditions"),Conditions,16,Error)) return false;
    TSet<FName> EffectIds,RuleIds;
    for (const auto& Value : *Effects)
    { FWarAbilityEffect E; if (!ReadEffect(ValueObject(Value),E,A.bLegacyTargeting,false,Error) || EffectIds.Contains(E.Id)) return Fail(Error,TEXT("Duplicate or invalid applied effect.")); EffectIds.Add(E.Id); A.Effects.Add(MoveTemp(E)); }
    if (A.Effects.IsEmpty() && A.UnavailableReason.IsEmpty()) return Fail(Error,TEXT("Applied ability has no effects or recorded unavailable reason."));
    for (const auto& Value : *Conditions)
    {
        auto R = ValueObject(Value); FWarConditionalRule Rule;
        if (!Exact(R,{TEXT("id"),TEXT("event"),TEXT("name"),TEXT("condition"),TEXT("actions")},Error)
            || !ReadName(R,TEXT("id"),Rule.Id,Error) || !ReadName(R,TEXT("event"),Rule.Event,Error) || !ReadString(R,TEXT("name"),Rule.Name,512,Error)
            || Rule.Id.IsNone() || RuleIds.Contains(Rule.Id) || !OneOf(Rule.Event,{TEXT("cast_start"),TEXT("application"),TEXT("tick")}))
            return Fail(Error,TEXT("Invalid conditional rule identity or event."));
        RuleIds.Add(Rule.Id); int32 Leaves = 0;
        if (!ReadCondition(Child(R,TEXT("condition")),Rule.Condition,1,Leaves,Error) || !OneOf(Rule.Condition.Kind,{TEXT("all"),TEXT("any")})) return false;
        const TArray<TSharedPtr<FJsonValue>>* Actions;
        if (!ReadArray(R,TEXT("actions"),Actions,32,Error) || Actions->IsEmpty()) return Fail(Error,TEXT("Rule has no bounded actions."));
        TSet<FString> Modifiers;
        for (const auto& Item : *Actions)
        {
            auto J = ValueObject(Item); FWarConditionalAction Action;
            if (!Exact(J,{TEXT("kind"),TEXT("effectId"),TEXT("value"),TEXT("effect")},Error) || !ReadName(J,TEXT("kind"),Action.Kind,Error)
                || !ReadName(J,TEXT("effectId"),Action.EffectId,Error) || !ReadNumber(J,TEXT("value"),Action.Value,Error,-1000000)
                || !OneOf(Action.Kind,{TEXT("add_effect"),TEXT("flat"),TEXT("percent")})) return Fail(Error,TEXT("Invalid conditional action."));
            const bool Bonus = Action.Kind == TEXT("add_effect");
            if (!ReadEffect(Child(J,TEXT("effect")),Action.Effect,A.bLegacyTargeting,!Bonus,Error)) return false;
            if (Bonus)
            {
                if (EffectIds.Contains(Action.Effect.Id) || !OneOf(Action.Effect.Kind,{TEXT("damage"),TEXT("heal"),TEXT("status"),TEXT("player_status")})
                    || (Rule.Event == TEXT("tick") && (Action.Effect.PeriodicDuration > 0 || OneOf(Action.Effect.StatusKind,{TEXT("burn"),TEXT("bleed")}))))
                    return Fail(Error,TEXT("Invalid immutable bonus identity or recursive periodic scheduler."));
                EffectIds.Add(Action.Effect.Id);
            }
            else
            {
                const auto* Base = A.Effects.FindByPredicate([&](const auto& E){return E.Id == Action.EffectId;});
                const FString Key = Name(Action.Kind) + TEXT(":") + Name(Action.EffectId);
                if (!Base || !OneOf(Base->Kind,{TEXT("damage"),TEXT("heal")}) || Modifiers.Contains(Key)
                    || (Action.Kind == TEXT("percent") && (Action.Value < -1 || Action.Value > 100))
                    || (Rule.Event == TEXT("tick") && Base->PeriodicDuration <= 0 && A.TimingMode != TEXT("channel")))
                    return Fail(Error,TEXT("Invalid immutable conditional amount modifier."));
                Modifiers.Add(Key);
            }
            Rule.Actions.Add(MoveTemp(Action));
        }
        if (Rule.Event == TEXT("tick") && A.TimingMode != TEXT("channel") && !A.Effects.ContainsByPredicate([](const auto& E){return E.PeriodicDuration > 0;}))
            return Fail(Error,TEXT("Tick condition has no immutable periodic effect or channel."));
        A.Conditions.Add(MoveTemp(Rule));
    }
    if (A.PreparationScale < .1f || A.PreparationScale > 1 || A.ResourceMax <= 0 || A.ResourceInitial > A.ResourceMax
        || A.ReleaseFraction < .05f || A.ReleaseFraction > .95f || A.Cooldown > 3600 || A.Gcd > 60 || A.TickInterval < .1f
        || (!A.TimingMode.IsNone() && !OneOf(A.TimingMode,{TEXT("instant"),TEXT("cast"),TEXT("channel")})))
        return Fail(Error,TEXT("Applied timing or resource bounds are invalid."));
    Out = MoveTemp(A); return true;
}

bool WarCampaignCombatDefinition::Encode(const FWarAbilityDefinition& Definition, FString& Payload, FString& Sha256, FString& Error)
{
    Payload.Reset(); Sha256.Reset(); Error.Reset(); const auto Row = WriteDefinition(Definition,Error); if (!Row) return false;
    FString Candidate;
    if (!FJsonSerializer::Serialize(Row.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Candidate))
        || !WarCitadelProofHash::Text(Candidate,Sha256,Error)) return Fail(Error,TEXT("Immutable native value serialization or SHA failed."));
    FWarAbilityDefinition Checked;
    if (!Decode(Candidate,Sha256,Checked,Error)) { Sha256.Reset(); return false; }
    Payload = MoveTemp(Candidate); return true;
}

#undef DEFINITION_NAMES
#undef DEFINITION_STRINGS
#undef DEFINITION_NUMBERS
#undef DEFINITION_BOOLEANS
#undef EFFECT_NAMES
#undef EFFECT_NUMBERS
#undef CONDITION_NAMES
