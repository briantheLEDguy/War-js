#include "SWarAbilityWorkshop.h"
#include "WarAbilityWorkshopSubsystem.h"
#include "WarAbilityConditions.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

using namespace WarWorkshopJson;

bool SWarAbilityWorkshop::VerifyAnalysis(FString& Error)
{
    ApplyComposer(); if (bDirtyComposer) { Error=Notice; return false; }
    Tab=TEXT("Test Arena"); Build();
    auto Status=Parse(TEXT(R"({"category":"dot","subject":"target","source":"self","expires":30,"effectId":"proof_dot"})")); Status->SetStringField(TEXT("abilityId"),SelectedAbility);
    Scenario->SetArrayField(TEXT("statuses"),{MakeShared<FJsonValueObject>(Status)}); Scenario->SetStringField(TEXT("targetRealm"),TEXT("riftbound")); Scenario->SetNumberField(TEXT("now"),10); ++ScenarioSerial;
    PreviewScenario(); if (!Analysis.Contains(TEXT("PASS"))) { Error=TEXT("Starting DoT did not qualify the calculated preview."); return false; }
    Scenario->SetNumberField(TEXT("now"),31); ++ScenarioSerial;
    if (AnalysisScenario==ScenarioSerial) { Error=TEXT("Changed scenario did not invalidate its result."); return false; }
    PreviewScenario(); if (!Analysis.Contains(TEXT("FAIL"))) { Error=TEXT("Expired starting status still qualified."); return false; }
    Scenario->SetNumberField(TEXT("now"),10); ++ScenarioSerial; PreviewScenario(); BuildSpecialPage();
    return true;
}

void SWarAbilityWorkshop::BuildScenario()
{
    if (!Scenario) Scenario=Parse(TEXT(R"({"level":1,"stat":10,"spent":0,"mana":100,"defense":0,"targets":1,"window":10,"maxHealth":100,"missingHealth":100,"now":0,"event":"application","recipient":"target","targetRealm":"aegis","castingState":"recovery","statuses":[]})"));
    if (SelectedAbility.IsEmpty() && !Array(Store->Document().Get(),TEXT("abilities")).IsEmpty()) SelectedAbility=Text(Array(Store->Document().Get(),TEXT("abilities"))[0]->AsObject(),TEXT("id"));
    SpecialPage->AddSlot().AutoHeight().Padding(0,20,0,8)[Label(TEXT("Balance analysis · calculated event snapshot"))];
    SpecialPage->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).AutoWrapText(true).Text(FText::FromString(TEXT("Mean damage/healing rolls with the entered defenses. Statuses remain fixed for this estimate; travel, later status changes, movement, immunities and other combatants are not simulated. The online executor must verify those interactions.")))];
    SpecialPage->AddSlot().AutoHeight().Padding(0,10)[AbilityPicker(SelectedAbility,[this](FString Id) { SelectedAbility=Id; SelectedAssignment.Reset(); ++ScenarioSerial; BuildSpecialPage(); })];
    if (!SelectedAssignment.IsEmpty()) SpecialPage->AddSlot().AutoHeight()[Label(TEXT("Uses numeric overrides from the selected class assignment."),true)];
    auto Layout=SNew(SHorizontalBox); auto Controls=SNew(SVerticalBox),Output=SNew(SVerticalBox);
    Layout->AddSlot().AutoWidth()[SNew(SBox).WidthOverride(390)[Controls]];
    Layout->AddSlot().FillWidth(1).Padding(24,0)[Output]; SpecialPage->AddSlot().AutoHeight()[Layout];
    const auto Numeric=[this,Controls](const TCHAR* Key,const TCHAR* Name,double Min,double Max,bool Integer=false) {
        Controls->AddSlot().AutoHeight()[NumericField(Name,Number(Scenario,Key),[this,Key,Min,Max,Integer](double V) {
            if (V<Min || V>Max || (Integer && V!=FMath::FloorToDouble(V))) { Notice=TEXT("Scenario value is outside its displayed range."); return; } Scenario->SetNumberField(Key,V); ++ScenarioSerial;
        })]; };
    Numeric(TEXT("level"),TEXT("Level (1–45)"),1,45,true); Numeric(TEXT("stat"),TEXT("Scaling stat (0–10,000)"),0,10000);
    Numeric(TEXT("spent"),TEXT("Class resource spent (0–10,000)"),0,10000); Numeric(TEXT("mana"),TEXT("Available mana"),0,10000);
    Numeric(TEXT("defense"),TEXT("Damage reduction (0–1)"),0,1); Numeric(TEXT("targets"),TEXT("Identical recipients (1–128)"),1,128,true);
    Numeric(TEXT("window"),TEXT("Estimate window (seconds, 0–60)"),0,60); Numeric(TEXT("maxHealth"),TEXT("Recipient maximum health"),1,1000000);
    Numeric(TEXT("missingHealth"),TEXT("Recipient missing health"),0,1000000); Numeric(TEXT("now"),TEXT("Evaluation time (seconds)"),0,3600);
    Controls->AddSlot().AutoHeight().Padding(0,10)[Choice(Text(Scenario,TEXT("event")),{{TEXT("cast_start"),TEXT("Cast start")},{TEXT("application"),TEXT("Impact / application")},{TEXT("tick"),TEXT("Periodic tick")}},[this](FString V) { Scenario->SetStringField(TEXT("event"),V); ++ScenarioSerial; })];
    Controls->AddSlot().AutoHeight()[Choice(Text(Scenario,TEXT("recipient")),{{TEXT("target"),TEXT("Recipient is selected target")},{TEXT("caster"),TEXT("Recipient is caster")}},[this](FString V) { Scenario->SetStringField(TEXT("recipient"),V); ++ScenarioSerial; })];
    Controls->AddSlot().AutoHeight().Padding(0,10)[Choice(Text(Scenario,TEXT("targetRealm")),{{TEXT("aegis"),TEXT("Allied target")},{TEXT("riftbound"),TEXT("Enemy target")}},[this](FString V) { Scenario->SetStringField(TEXT("targetRealm"),V); ++ScenarioSerial; })];
    Controls->AddSlot().AutoHeight()[Label(TEXT("Target execution state"))];
    Controls->AddSlot().AutoHeight()[AbilityPicker(Text(Scenario,TEXT("castingAbility")),[this](FString V) { Scenario->SetStringField(TEXT("castingAbility"),V); ++ScenarioSerial; BuildSpecialPage(); })];
    Controls->AddSlot().AutoHeight()[Choice(Text(Scenario,TEXT("castingState")),{{TEXT("casting"),TEXT("Casting")},{TEXT("channeling"),TEXT("Channeling")},{TEXT("recovery"),TEXT("Recovery / no active cast")}},[this](FString V) { Scenario->SetStringField(TEXT("castingState"),V); ++ScenarioSerial; })];
    Controls->AddSlot().AutoHeight().Padding(0,10)[Label(TEXT("Caster execution state"))];
    Controls->AddSlot().AutoHeight()[AbilityPicker(Text(Scenario,TEXT("casterAbility")),[this](FString V) { Scenario->SetStringField(TEXT("casterAbility"),V); ++ScenarioSerial; BuildSpecialPage(); })];
    Controls->AddSlot().AutoHeight()[Choice(Text(Scenario,TEXT("casterState")),{{TEXT("casting"),TEXT("Casting")},{TEXT("channeling"),TEXT("Channeling")},{TEXT("recovery"),TEXT("Recovery / no active cast")}},[this](FString V) { Scenario->SetStringField(TEXT("casterState"),V); ++ScenarioSerial; })];
    Output->AddSlot().AutoHeight()[Button(TEXT("Calculate this snapshot"),[this] { PreviewScenario(); })];
    Output->AddSlot().AutoHeight().Padding(0,12)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).AutoWrapText(true).Text_Lambda([this] {
        return FText::FromString(Analysis.IsEmpty() ? TEXT("No calculated result yet. Configure starting statuses below, then calculate.") : ((Store->Document().Serial()!=AnalysisDraft || ScenarioSerial!=AnalysisScenario) ? TEXT("OUTDATED · the draft or scenario changed.\n\n") : TEXT(""))+Analysis);
    })];
    for (const auto& V:Array(Scenario,TEXT("statuses")))
    {
        const auto S=V->AsObject(); Output->AddSlot().AutoHeight().Padding(0,16,0,4)[Label(TEXT("Starting ")+Text(S,TEXT("category")))];
        Output->AddSlot().AutoHeight()[Choice(Text(S,TEXT("subject")),{{TEXT("caster"),TEXT("On caster")},{TEXT("target"),TEXT("On target")}},[this,S](FString V) { S->SetStringField(TEXT("subject"),V); ++ScenarioSerial; })];
        Output->AddSlot().AutoHeight()[AbilityPicker(Text(S,TEXT("abilityId")),[this,S](FString V) { S->SetStringField(TEXT("abilityId"),V); S->SetStringField(TEXT("effectId"),TEXT("")); ++ScenarioSerial; BuildSpecialPage(); })];
        Output->AddSlot().AutoHeight()[EffectPicker(Text(S,TEXT("abilityId")),Text(S,TEXT("effectId")),[this,S](FString V) { S->SetStringField(TEXT("effectId"),V); ++ScenarioSerial; BuildSpecialPage(); })];
        Output->AddSlot().AutoHeight()[Choice(Text(S,TEXT("source")),{{TEXT("self"),TEXT("Applied by this caster")},{TEXT("allied"),TEXT("Applied by another ally")},{TEXT("enemy"),TEXT("Applied by an enemy")}},[this,S](FString V) { S->SetStringField(TEXT("source"),V); ++ScenarioSerial; })];
        Output->AddSlot().AutoHeight()[NumericField(TEXT("Expires at (seconds)"),Number(S,TEXT("expires")),[this,S](double V) { if (V>=0 && V<=3600) { S->SetNumberField(TEXT("expires"),V); ++ScenarioSerial; } })];
        if (Text(S,TEXT("category"))==TEXT("shield")) Output->AddSlot().AutoHeight()[NumericField(TEXT("Shield remaining (0 means depleted)"),Number(S,TEXT("remaining")),[this,S](double V) { if (V>=0 && V<=1000000) { S->SetNumberField(TEXT("remaining"),V); ++ScenarioSerial; } })];
        Output->AddSlot().AutoHeight()[Button(TEXT("Remove starting status"),[this,S] { auto Values=Array(Scenario,TEXT("statuses")); Values.RemoveAll([&](const auto& V) { return V->AsObject()==S; }); Scenario->SetArrayField(TEXT("statuses"),Values); ++ScenarioSerial; BuildSpecialPage(); })];
    }
    for (const FString Kind:{TEXT("hot"),TEXT("dot"),TEXT("status"),TEXT("shield")}) Output->AddSlot().AutoHeight().Padding(0,8)[Button(TEXT("+ Starting ")+Kind,[this,Kind] {
        auto Values=Array(Scenario,TEXT("statuses")); if (Values.Num()>=16) { Notice=TEXT("Preview allows 16 starting statuses."); return; }
        auto S=Parse(TEXT(R"({"subject":"target","source":"self","expires":30})")); S->SetStringField(TEXT("category"),Kind); S->SetStringField(TEXT("abilityId"),SelectedAbility);
        S->SetNumberField(TEXT("remaining"),25);
        const auto A=Find(Store->Document().Get(),TEXT("abilities"),SelectedAbility); if (!Array(A,TEXT("effects")).IsEmpty()) S->SetStringField(TEXT("effectId"),Text(Array(A,TEXT("effects"))[0]->AsObject(),TEXT("id")));
        Values.Add(MakeShared<FJsonValueObject>(S)); Scenario->SetArrayField(TEXT("statuses"),Values); ++ScenarioSerial; BuildSpecialPage();
    })];
}

void SWarAbilityWorkshop::PreviewScenario()
{
    if (!Store.IsValid() || !Scenario) return; const auto W=Store->Document().Get(); FString Error;
    auto A=SelectedAssignment.IsEmpty() ? Clone(Find(W,TEXT("abilities"),SelectedAbility)) : FWarAbilityWorkshopDocument::Effective(W,Find(W,TEXT("assignments"),SelectedAssignment),Error);
    if (!A) { Notice=TEXT("Select a committed ability."); return; }
    TArray<FWarConditionalRule> Rules; if (!WarAbilityConditions::ParseRules(A,Rules,Error)) { Notice=Error; return; }
    FWarConditionContext C; C.Now=Number(Scenario,TEXT("now")); C.Caster.Id=TEXT("caster"); C.Caster.Realm=TEXT("aegis"); C.Caster.bAlive=true;
    C.Target.Id=TEXT("target"); C.Target.Realm=FName(*Text(Scenario,TEXT("targetRealm"))); C.Target.bAlive=true;
    C.Target.CastingAbility=FName(*Text(Scenario,TEXT("castingAbility"))); C.Target.ActionState=FName(*Text(Scenario,TEXT("castingState")));
    C.Caster.CastingAbility=FName(*Text(Scenario,TEXT("casterAbility"))); C.Caster.ActionState=FName(*Text(Scenario,TEXT("casterState")));
    for (const auto& V:Array(Scenario,TEXT("statuses")))
    {
        const auto S=V->AsObject(); FWarStatusObservation O; O.AbilityId=FName(*Text(S,TEXT("abilityId"))); O.EffectId=FName(*Text(S,TEXT("effectId"))); O.Category=FName(*Text(S,TEXT("category"))); O.Expires=Number(S,TEXT("expires"));
        O.Remaining=Number(S,TEXT("remaining"));
        const FString Source=Text(S,TEXT("source")); O.SourceId=Source==TEXT("self") ? TEXT("caster") : Source==TEXT("allied") ? TEXT("other_ally") : TEXT("enemy_caster"); O.SourceRealm=Source==TEXT("enemy") ? TEXT("riftbound") : TEXT("aegis");
        (Text(S,TEXT("subject"))==TEXT("caster") ? C.Caster : C.Target).Statuses.Add(O);
    }
    C.Recipient=Text(Scenario,TEXT("recipient"))==TEXT("caster") ? C.Caster : C.Target;
    const FName Event(*Text(Scenario,TEXT("event"))); TArray<FWarRuleEvaluation> Evaluations;
    Evaluations.Add(WarAbilityConditions::Evaluate(Rules,TEXT("cast_start"),C));
    if (Event!=TEXT("cast_start")) Evaluations.Add(WarAbilityConditions::Evaluate(Rules,TEXT("application"),C));
    const auto Tick=Event==TEXT("tick") ? WarAbilityConditions::Evaluate(Rules,TEXT("tick"),C) : FWarRuleEvaluation();
    TArray<FString> Lines; Lines.Add(FString::Printf(TEXT("CALCULATED · shared revision %.0f · local edit %llu\nUnconditional → conditional · mean roll\n"),Number(W,TEXT("revision")),Store->Document().Serial()));
    double Damage=0,Healing=0; const double Targets=Number(Scenario,TEXT("targets")),Window=Number(Scenario,TEXT("window"));
    const auto Describe=[&](const FWarAbilityEffect& E,bool Bonus) {
        const float Raw=WarAbilities::RawAmount(E,Number(Scenario,TEXT("stat")),Number(Scenario,TEXT("level")),Number(Scenario,TEXT("spent")),.5f);
        const float Base=WarAbilityConditions::Amount(Raw,E.Id,{}); float Value=Bonus ? Base : WarAbilityConditions::Amount(Raw,E.Id,Evaluations);
        if (!Bonus && Event==TEXT("tick") && E.PeriodicDuration>0) Value=WarAbilityConditions::Amount(Value,E.Id,{Tick});
        const double Count=E.Recipient==TEXT("caster") ? 1 : Targets;
        const double Ticks=E.PeriodicDuration>0 ? FMath::FloorToDouble(FMath::Min(Window,double(E.PeriodicDuration))/E.Interval) : 1;
        if (E.Kind==TEXT("damage") || E.Kind==TEXT("heal")) {
            Lines.Add(FString::Printf(TEXT("%s%s %s: %.0f → %.0f%s"),Bonus ? TEXT("Bonus · ") : TEXT(""),*E.Id.ToString(),*E.Kind.ToString(),Bonus ? 0 : Base,Value,E.PeriodicDuration>0 ? TEXT(" per tick") : TEXT("")));
            if (!Bonus) { if (E.Kind==TEXT("damage")) Damage+=Value*Count*Ticks*(1-Number(Scenario,TEXT("defense"))); else Healing+=Value*Count*Ticks; }
        }
        else if (E.StatusKind==TEXT("shield")) Lines.Add(FString::Printf(TEXT("%sShield capacity %.0f · %.2fs"),Bonus ? TEXT("Bonus · ") : TEXT(""),E.bHasAmount ? Value : Number(Scenario,TEXT("maxHealth"))*E.Magnitude,E.Duration));
        else if (E.Kind==TEXT("status") || E.Kind==TEXT("player_status")) Lines.Add(FString::Printf(TEXT("%s%s · %.2fs · magnitude %.2f"),Bonus ? TEXT("Bonus · ") : TEXT(""),*E.StatusKind.ToString(),E.Duration,E.Magnitude));
    };
    for (const auto& V:Array(A,TEXT("effects"))) { FWarAbilityEffect E; if (!WarAbilityConditions::ParseEffect(V->AsObject(),E,Error)) { Notice=Error; return; } Describe(E,false); }
    for (const auto& R:Evaluations) for (const auto& E:R.BonusEffects) Describe(E,true);
    for (const auto& E:Tick.BonusEffects) Describe(E,true);
    Lines.Add(FString::Printf(TEXT("\nBase-effect projection / %.1fs / %.0f recipients:\nDamage %.0f · healing %.0f · effective healing at most %.0f\nMana cost %.0f / available %.0f\nAdditional effect scheduling is excluded from these totals. The entered recipient snapshot is used for each component; the executor resolves recipients separately."),Window,Targets,Damage,Healing,FMath::Min(Healing,Number(Scenario,TEXT("missingHealth"))*Targets),Number(Object(A,TEXT("resource")),TEXT("manaCost")),Number(Scenario,TEXT("mana"))));
    if (Number(Object(A,TEXT("resource")),TEXT("manaCost"))>Number(Scenario,TEXT("mana"))) Lines.Add(TEXT("Activation would fail: insufficient mana."));
    auto Traced=Evaluations; if (Event==TEXT("tick")) Traced.Add(Tick);
    for (const auto& R:Traced) for (const auto& T:R.Traces) {
        Lines.Add(FString::Printf(TEXT("\n%s · %s · %s · %.2fs · recipient %s"),*T.RuleId.ToString(),*T.Event.ToString(),T.bPassed ? TEXT("PASS") : TEXT("FAIL"),T.At,*T.RecipientId.ToString()));
        for (const auto& P:T.Predicates) { TArray<FString> Sources; for (const auto& S:P.Sources) Sources.Add(S.ToString()); Lines.Add(P.Path+(P.bPassed ? TEXT(" PASS ") : TEXT(" FAIL "))+P.SubjectId.ToString()+TEXT(" · sources: ")+FString::Join(Sources,TEXT(", "))); }
    }
    Analysis=FString::Join(Lines,TEXT("\n")); AnalysisDraft=Store->Document().Serial(); AnalysisScenario=ScenarioSerial;
}
