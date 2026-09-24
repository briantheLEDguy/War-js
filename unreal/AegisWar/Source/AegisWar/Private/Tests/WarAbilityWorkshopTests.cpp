#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarAbilityConditions.h"
#include "WarAbilityWorkshopDocument.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityConditionalTest,"AegisWar.Foundation.AbilityConditions",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarAbilityConditionalTest::RunTest(const FString& Parameters)
{
    FWarConditionContext C; C.Now=10; C.Caster.Id=TEXT("caster"); C.Caster.Realm=TEXT("aegis"); C.Caster.bAlive=true;
    C.Recipient.Id=TEXT("ally"); C.Recipient.Realm=TEXT("aegis"); C.Recipient.bAlive=true;
    FWarStatusObservation Status; Status.AbilityId=TEXT("renewal"); Status.EffectId=TEXT("hot"); Status.SourceId=C.Caster.Id; Status.SourceRealm=C.Caster.Realm; Status.Category=TEXT("hot"); Status.Expires=20;
    C.Recipient.Statuses.Add(Status);
    FWarAbilityCondition Predicate; Predicate.Kind=TEXT("hot"); Predicate.Subject=TEXT("recipient"); Predicate.Source=TEXT("self");
    FWarConditionalRule Rule; Rule.Id=TEXT("renewal_bonus"); Rule.Event=TEXT("application"); Rule.Condition.Kind=TEXT("all"); Rule.Condition.Children.Add(Predicate);
    FWarConditionalAction Percent; Percent.Kind=TEXT("percent"); Percent.EffectId=TEXT("heal"); Percent.Value=.25;
    FWarConditionalAction Flat=Percent; Flat.Kind=TEXT("flat"); Flat.Value=20; Rule.Actions={Percent,Flat};
    auto Evaluate=[&] { return WarAbilityConditions::Evaluate({Rule},Rule.Event,C); };
    auto Result=Evaluate();
    TestEqual(TEXT("Flat bonuses precede percentages"),WarAbilityConditions::Amount(100,TEXT("heal"),{Result}),150.f);
    FWarAbilityEffect Fraction; Fraction.Minimum=.4f; Fraction.Maximum=.4f;
    TestEqual(TEXT("Round after conditional arithmetic"),WarAbilityConditions::Amount(WarAbilities::RawAmount(Fraction,0,1,0,0),TEXT("heal"),{Result}),26.f);
    TestEqual(TEXT("Zero remains zero"),WarAbilityConditions::Amount(0,TEXT("heal"),{}),0.f);
    TestEqual(TEXT("Trace records source"),Result.Traces[0].Predicates[0].Sources[0],C.Caster.Id);
    C.Caster.Id=TEXT("other"); TestFalse(TEXT("Own HoT excludes another caster"),Evaluate().Traces[0].bPassed);
    Rule.Condition.Children[0].Source=TEXT("allied"); TestTrue(TEXT("Allied HoT includes another ally"),Evaluate().Traces[0].bPassed);
    C.Now=20; TestFalse(TEXT("Expiry equality is inactive"),Evaluate().Traces[0].bPassed);
    Rule.Condition.Children[0].bNot=true; C.Recipient.bAlive=false; TestFalse(TEXT("Dead subject cannot satisfy negation"),Evaluate().Traces[0].bPassed);
    C.Recipient.bAlive=true; C.Now=10; Rule.Condition.Children[0].bNot=false;
    Rule.Condition.Children[0].Kind=TEXT("casting"); Rule.Condition.Children[0].AbilityId=TEXT("spell");
    C.Recipient.CastingAbility=TEXT("spell"); C.Recipient.ActionState=TEXT("casting"); TestTrue(TEXT("Casting qualifies"),Evaluate().Traces[0].bPassed);
    C.Recipient.ActionState=TEXT("channeling"); TestTrue(TEXT("Channeling qualifies"),Evaluate().Traces[0].bPassed);
    C.Recipient.ActionState=TEXT("recovery"); TestFalse(TEXT("Recovery does not qualify"),Evaluate().Traces[0].bPassed);
    for (int32 Tick=0; Tick<5; ++Tick) TestEqual(TEXT("A tick starts from its stored baseline"),WarAbilityConditions::Amount(100,TEXT("heal"),{Result}),150.f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityConditionalValidationTest,"AegisWar.Foundation.AbilityConditionValidation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarAbilityConditionalValidationTest::RunTest(const FString& Parameters)
{
    const FString Json=TEXT(R"({"conditions":[{"id":"bonus","event":"application","condition":{"kind":"all","children":[{"kind":"hot","subject":"recipient","source":"self"}]},"actions":[{"kind":"percent","effectId":"heal","value":0.25}]}]})");
    TSharedPtr<FJsonObject> Row; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Row);
    FWarAbilityDefinition A; A.Id=TEXT("custom.heal"); A.Shape=TEXT("area"); FWarAbilityEffect Effect; Effect.Id=TEXT("heal"); Effect.Kind=TEXT("heal"); A.Effects.Add(Effect);
    FString Error;
    TestTrue(TEXT("Typed rules parse"),WarAbilityConditions::ParseRules(Row,A.Conditions,Error));
    TestTrue(TEXT("Application recipient accepted"),WarAbilityConditions::Validate(A,{A},Error));
    A.Conditions[0].Event=TEXT("cast_start"); TestFalse(TEXT("Unknown area recipients rejected at cast start"),WarAbilityConditions::Validate(A,{A},Error));
    A.Conditions[0].Event=TEXT("tick"); TestFalse(TEXT("Tick without scheduler rejected"),WarAbilityConditions::Validate(A,{A},Error));
    A.Effects[0].PeriodicDuration=5; TestTrue(TEXT("Periodic amount modifier accepted"),WarAbilityConditions::Validate(A,{A},Error));
    FWarConditionalAction Bonus; Bonus.Kind=TEXT("add_effect"); Bonus.Effect=Effect; Bonus.Effect.Id=TEXT("extra_hot"); Bonus.Effect.PeriodicDuration=5;
    A.Conditions[0].Actions.Add(Bonus); TestFalse(TEXT("Tick scheduler recursion rejected"),WarAbilityConditions::Validate(A,{A},Error));
    A.Conditions[0].Actions.Pop(); A.Conditions[0].Condition.Children[0].Kind=TEXT("effect"); A.Conditions[0].Condition.Children[0].AbilityId=TEXT("missing");
    TestFalse(TEXT("Missing dependencies rejected"),WarAbilityConditions::Validate(A,{A},Error));
    A.Conditions[0].Event=TEXT("application"); A.Conditions[0].Condition.Children[0].AbilityId=A.Id;
    A.Conditions[0].Condition.Children[0].EffectId=Bonus.Effect.Id; A.Conditions[0].Actions.Add(Bonus);
    TestTrue(TEXT("A specific-effect predicate can reference a conditional bonus"),WarAbilityConditions::Validate(A,{A},Error));
    A.Conditions[0].Actions.Pop();
    TestFalse(TEXT("Removing a referenced bonus is rejected"),WarAbilityConditions::Validate(A,{A},Error));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityWorkshopDocumentTest,"AegisWar.Foundation.AbilityWorkshopDocument",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarAbilityWorkshopDocumentTest::RunTest(const FString& Parameters)
{
    using namespace WarWorkshopJson;
    FString Json,Error;
    if (!TestTrue(TEXT("Staged baseline is available"),FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("Migration/content.json"))))) return false;
    FWarAbilityWorkshopDocument Doc;
    TSharedPtr<FJsonObject> Manifest;
    if (!TestTrue(TEXT("Content manifest parses"),FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Manifest))) return false;
    const bool Loaded=Doc.Baseline(Manifest,Error); if (!TestTrue(*Error,Loaded)) return false;
    TestEqual(TEXT("Baseline assignments retained"),Array(Doc.Get(),TEXT("assignments")).Num(),240);
    auto Empty=Clone(Doc.Get()); Empty->SetArrayField(TEXT("assignments"),{}); TArray<FWarAbilityDefinition> EmptyDefinitions;
    TestTrue(TEXT("Removing the final assignment is a valid complete workspace"),FWarAbilityWorkshopDocument::Compile(Empty,EmptyDefinitions,Error));
    TestTrue(TEXT("Removed assignments produce no future activations"),EmptyDefinitions.IsEmpty());
    const auto Assignment=Array(Doc.Get(),TEXT("assignments"))[0]->AsObject(); const FString Id=Text(Assignment,TEXT("id"));
    const FString Before=Serialize(Doc.Get());
    TestFalse(TEXT("Hidden edit rejected"),Doc.EditCells({{Id,TEXT("cooldownSec"),TEXT("set"),42}},{},Error));
    TestEqual(TEXT("Rejected edit is atomic"),Serialize(Doc.Get()),Before);
    TestTrue(TEXT("Visible numeric override"),Doc.EditCells({{Id,TEXT("cooldownSec"),TEXT("set"),42}},{Id},Error));
    TestEqual(TEXT("Effective override applies"),Number(FWarAbilityWorkshopDocument::Effective(Doc.Get(),Find(Doc.Get(),TEXT("assignments"),Id),Error),TEXT("cooldownSec")),42.);
    TestTrue(TEXT("Undo"),Doc.Undo()); TestEqual(TEXT("Undo preserves baseline"),Serialize(Doc.Get()),Before);
    TestTrue(TEXT("Redo"),Doc.Redo()); Doc.Undo();
    auto Broken=Clone(Doc.Get()); auto Unassigned=Clone(Array(Broken,TEXT("abilities"))[0]->AsObject()); Unassigned->SetStringField(TEXT("id"),TEXT("custom.unassigned"));
    auto Definitions=Array(Broken,TEXT("abilities")); Definitions.Add(MakeShared<FJsonValueObject>(Unassigned)); Broken->SetArrayField(TEXT("abilities"),Definitions);
    TestTrue(TEXT("Unassigned draft compiles"),Doc.Commit(Broken,Error));
    const auto Rules=Parse(TEXT(R"({"conditions":[{"id":"r","event":"application","condition":{"kind":"all","children":[{"kind":"ability_effect","subject":"caster","source":"self","abilityId":"custom.unassigned"}]},"actions":[{"kind":"add_effect","effect":{"id":"bonus","kind":"heal","recipient":"caster","amount":{"min":1,"max":1}}}]}]})"));
    Broken=Clone(Doc.Get()); Array(Broken,TEXT("abilities"))[0]->AsObject()->SetArrayField(TEXT("conditions"),Array(Rules,TEXT("conditions")));
    TestTrue(TEXT("Dependencies may refer to an unassigned definition"),Doc.Commit(Broken,Error));
    Broken=Clone(Doc.Get()); auto Values=Array(Broken,TEXT("abilities")); Values.RemoveAt(Values.Num()-1); Broken->SetArrayField(TEXT("abilities"),Values);
    TestFalse(TEXT("Removing referenced definition blocks the whole transaction"),Doc.Commit(Broken,Error));
    auto Base=Parse(TEXT(R"({"revision":1,"abilities":[{"id":"a","name":"Heal","cooldown":2,"amount":10}]})"));
    auto Current=Clone(Base),Yours=Clone(Base); Array(Current,TEXT("abilities"))[0]->AsObject()->SetStringField(TEXT("name"),TEXT("Renewal"));
    Array(Yours,TEXT("abilities"))[0]->AsObject()->SetNumberField(TEXT("amount"),20);
    TArray<FWarWorkshopConflict> Conflicts;
    auto Merged=FWarAbilityWorkshopDocument::Merge(Base,Current,Yours,{},Conflicts);
    TestTrue(TEXT("Nonoverlapping changes merge"),Conflicts.IsEmpty());
    TestEqual(TEXT("Merge retains current rename"),Text(Array(Merged,TEXT("abilities"))[0]->AsObject(),TEXT("name")),FString(TEXT("Renewal")));
    TestEqual(TEXT("Merge retains local amount"),Number(Array(Merged,TEXT("abilities"))[0]->AsObject(),TEXT("amount")),20.);
    Array(Current,TEXT("abilities"))[0]->AsObject()->SetNumberField(TEXT("amount"),30);
    Merged=FWarAbilityWorkshopDocument::Merge(Base,Current,Yours,{},Conflicts);
    TestEqual(TEXT("Overlapping change requires explicit resolution"),Conflicts.Num(),1);
    Merged=FWarAbilityWorkshopDocument::Merge(Base,Current,Yours,{{TEXT("/abilities/a/amount"),true}},Conflicts);
    TestTrue(TEXT("Yours resolves exact conflicting field"),Conflicts.IsEmpty());
    TestEqual(TEXT("Resolved local value"),Number(Array(Merged,TEXT("abilities"))[0]->AsObject(),TEXT("amount")),20.);
    const auto Changes=FWarAbilityWorkshopDocument::Changes(Base,Yours);
    TestEqual(TEXT("Review contains only changed fields"),Changes.Num(),1);
    TestEqual(TEXT("Review field follows stable identity"),Changes[0].Path,FString(TEXT("/abilities/a/amount")));
    TestEqual(TEXT("Review before value"),Changes[0].Before->AsNumber(),10.);
    TestEqual(TEXT("Review after value"),Changes[0].After->AsNumber(),20.);
    const auto Ordered=Parse(TEXT(R"({"effects":[{"id":"a","amount":1},{"id":"b","amount":2}]})"));
    const auto Reordered=Parse(TEXT(R"({"effects":[{"id":"b","amount":2},{"id":"a","amount":1}]})"));
    const auto Reordering=FWarAbilityWorkshopDocument::Changes(Ordered,Reordered);
    TestEqual(TEXT("Reordering is one order change, not effect replacement"),Reordering.Num(),1);
    TestEqual(TEXT("Review identifies order change"),Reordering[0].Path,FString(TEXT("/effects/@order")));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityConformanceTest,"AegisWar.Foundation.AbilityConditionConformance",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarAbilityConformanceTest::RunTest(const FString& Parameters)
{
    using namespace WarWorkshopJson;
    FString Json,Error;
    const FString Path=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("../../tests/fixtures/ability-conditions.json"));
    if (!TestTrue(TEXT("Shared condition fixtures exist"),FFileHelper::LoadFileToString(Json,*Path))) return false;
    const auto Fixtures=Parse(Json);
    if (!TestNotNull(TEXT("Shared fixtures parse"),Fixtures.Get())) return false;
    const auto Observation=[](const TSharedPtr<FJsonObject>& J) {
        FWarCombatObservation O; if (!J) return O;
        O.Id=FName(*Text(J,TEXT("id"))); O.Realm=FName(*Text(J,TEXT("realm"))); J->TryGetBoolField(TEXT("alive"),O.bAlive);
        const auto Action=Object(J,TEXT("action")); O.CastingAbility=FName(*Text(Action,TEXT("abilityId"))); O.ActionState=FName(*Text(Action,TEXT("state")));
        for (const auto& Value:Array(J,TEXT("statuses"))) { const auto S=Value->AsObject(); FWarStatusObservation Status;
            Status.AbilityId=FName(*Text(S,TEXT("abilityId"))); Status.EffectId=FName(*Text(S,TEXT("effectId")));
            Status.SourceId=FName(*Text(S,TEXT("sourceId"))); Status.SourceRealm=FName(*Text(S,TEXT("sourceRealm")));
            Status.Category=FName(*Text(S,TEXT("category"))); Status.Expires=Number(S,TEXT("expiresAt")); Status.Remaining=Number(S,TEXT("remaining")); O.Statuses.Add(Status); }
        return O;
    };
    for (const auto& Value:Array(Fixtures,TEXT("cases")))
    {
        const auto Fixture=Value->AsObject(),Input=Object(Fixture,TEXT("context")),Expected=Object(Fixture,TEXT("expected"));
        const FString Name=Text(Fixture,TEXT("name")); TArray<FWarConditionalRule> Rules;
        if (!TestTrue(*(Name+TEXT(" parses: ")+Error),WarAbilityConditions::ParseRules(Fixture,Rules,Error))) continue;
        FWarConditionContext Context; Context.Now=Number(Input,TEXT("now")); Context.Caster=Observation(Object(Input,TEXT("caster")));
        Context.Target=Observation(Object(Input,TEXT("target"))); Context.Recipient=Observation(Object(Input,TEXT("recipient")));
        const auto Result=WarAbilityConditions::Evaluate(Rules,FName(*Text(Fixture,TEXT("event"))),Context);
        TestEqual(*(Name+TEXT(" amount")),WarAbilityConditions::Amount(Number(Fixture,TEXT("normal")),FName(*Text(Fixture,TEXT("effectId"))),{Result}),static_cast<float>(Number(Expected,TEXT("amount"))));
        const auto& Passed=Array(Expected,TEXT("passed")); const auto& Predicates=Array(Expected,TEXT("predicates")); const auto& Sources=Array(Expected,TEXT("sources"));
        TestEqual(*(Name+TEXT(" rule count")),Result.Traces.Num(),Passed.Num()); int32 P=0;
        for (int32 R=0;R<Result.Traces.Num();++R) { const auto& Trace=Result.Traces[R];
            if (Passed.IsValidIndex(R)) TestEqual(*(Name+TEXT(" rule result")),Trace.bPassed,Passed[R]->AsBool());
            TestEqual(*(Name+TEXT(" event time")),Trace.At,Context.Now);
            for (const auto& Predicate:Trace.Predicates) {
                if (Predicates.IsValidIndex(P)) TestEqual(*(Name+TEXT(" predicate")),Predicate.bPassed,Predicates[P]->AsBool());
                if (Sources.IsValidIndex(P)) { const auto& ExpectedSources=Sources[P]->AsArray(); TestEqual(*(Name+TEXT(" source count")),Predicate.Sources.Num(),ExpectedSources.Num());
                    for (int32 S=0;S<Predicate.Sources.Num() && S<ExpectedSources.Num();++S) TestEqual(*(Name+TEXT(" source")),Predicate.Sources[S],FName(*ExpectedSources[S]->AsString())); }
                ++P;
            }
        }
        TestEqual(*(Name+TEXT(" predicate count")),P,Predicates.Num());
        const auto& Bonus=Array(Expected,TEXT("bonusEffects")); TestEqual(*(Name+TEXT(" bonus count")),Result.BonusEffects.Num(),Bonus.Num());
        for (int32 I=0;I<Result.BonusEffects.Num() && I<Bonus.Num();++I) TestEqual(*(Name+TEXT(" bonus identity")),Result.BonusEffects[I].Id,FName(*Bonus[I]->AsString()));
    }
    return true;
}
#endif
