#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCampaignCombatDefinition.h"
#include "WarCitadelSiegeProof.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
    FWarAbilityDefinition AppliedDefinition()
    {
        FWarAbilityDefinition A;
        A.Id=TEXT("ember_arcanist.applied_flame"); A.Career=TEXT("ember_arcanist"); A.Version=TEXT("recorded-before-edit");
        A.Shape=TEXT("cone"); A.School=TEXT("fire"); A.AssignmentId=TEXT("library.assignment");
        A.TargetKind=TEXT("enemy"); A.TimingMode=TEXT("channel");
        A.Name=TEXT("Sentinel \u00e9 \U0001f6e1"); A.Summary=TEXT("First line\nSecond line \u76fe");
        A.UnavailableReason=TEXT("Retained reason"); A.ResourceLabel=TEXT("Heat");
        A.Slot=3; A.UnlockLevel=12; A.MaxTargets=18;
        A.bEnemyTarget=true; A.bSpendAll=true; A.bBlockedBySilence=true; A.bLegacyTargeting=false;
        A.bAuthoredTiming=true; A.bCancelOnMovement=true; A.PreparationScale=.5f;
        A.Range=1535; A.Radius=450; A.ProjectileSpeed=2000; A.Cooldown=23.5f; A.Gcd=1.2f;
        A.Mana=20; A.Build=5; A.Cost=4; A.MinimumResource=6; A.ResourceMax=100; A.ResourceInitial=2;
        A.ReleaseFraction=.45f; A.CastSeconds=1.4f; A.ChannelSeconds=3.2f; A.TickInterval=.5f;
        A.Presentations.Add(TEXT("profile_b"),TEXT("motion_b")); A.Presentations.Add(TEXT("profile_a"),TEXT("motion_a"));
        FWarAbilityEffect Damage;
        Damage.Id=TEXT("flame"); Damage.Recipient=TEXT("target"); Damage.Kind=TEXT("damage"); Damage.School=TEXT("fire");
        Damage.StatusId=TEXT("recorded_metadata"); Damage.StatusKind=TEXT("burn"); Damage.Modifier=TEXT("scorch");
        Damage.StackGroup=TEXT("fire"); Damage.Direction=TEXT("forward"); Damage.Label=TEXT("Recorded flame");
        Damage.Minimum=10; Damage.Maximum=25; Damage.StatScale=.8f; Damage.LevelScale=2; Damage.ResourceScale=.3f;
        Damage.Duration=4; Damage.Magnitude=.2f; Damage.Distance=100; Damage.PeriodicDuration=8; Damage.Interval=.5f;
        Damage.bHasAmount=true; Damage.Cleanse={TEXT("slow"),TEXT("root")}; A.Effects.Add(Damage);
        FWarAbilityEffect Status;
        Status.Id=TEXT("burn"); Status.Recipient=TEXT("target"); Status.Kind=TEXT("status"); Status.School=TEXT("fire");
        Status.StatusId=TEXT("burn"); Status.StatusKind=TEXT("burn"); Status.StackGroup=TEXT("fire");
        Status.Modifier=TEXT("scorch"); Status.Label=TEXT("Burn \u00e9"); Status.Duration=12; Status.Magnitude=.2f;
        A.Effects.Add(Status);
        FWarConditionalRule Rule; Rule.Id=TEXT("applied_condition"); Rule.Event=TEXT("application"); Rule.Name=TEXT("Original condition");
        Rule.Condition.Kind=TEXT("all"); FWarAbilityCondition Predicate;
        Predicate.Kind=TEXT("effect"); Predicate.Subject=TEXT("target"); Predicate.Source=TEXT("self");
        Predicate.AbilityId=A.Id; Predicate.EffectId=TEXT("burn"); Predicate.bNot=true; Rule.Condition.Children.Add(Predicate);
        FWarConditionalAction Flat; Flat.Kind=TEXT("flat"); Flat.EffectId=Damage.Id; Flat.Value=-7.5f; Rule.Actions.Add(Flat);
        FWarConditionalAction Percent; Percent.Kind=TEXT("percent"); Percent.EffectId=Damage.Id; Percent.Value=.25f; Rule.Actions.Add(Percent);
        FWarConditionalAction Bonus; Bonus.Kind=TEXT("add_effect"); Bonus.EffectId=TEXT("retained_action_metadata"); Bonus.Value=123;
        Bonus.Effect=Status; Bonus.Effect.Id=TEXT("bonus_burn"); Rule.Actions.Add(Bonus); A.Conditions.Add(Rule);
        return A;
    }
    bool SameEffect(const FWarAbilityEffect& A,const FWarAbilityEffect& B)
    {
        return A.Id==B.Id && A.Recipient==B.Recipient && A.Kind==B.Kind && A.School==B.School && A.StatusId==B.StatusId
            && A.StatusKind==B.StatusKind && A.Modifier==B.Modifier && A.StackGroup==B.StackGroup && A.Direction==B.Direction
            && A.Label==B.Label && A.Minimum==B.Minimum && A.Maximum==B.Maximum && A.StatScale==B.StatScale
            && A.LevelScale==B.LevelScale && A.ResourceScale==B.ResourceScale && A.Duration==B.Duration && A.Magnitude==B.Magnitude
            && A.Distance==B.Distance && A.PeriodicDuration==B.PeriodicDuration && A.Interval==B.Interval
            && A.bHasAmount==B.bHasAmount && A.Cleanse==B.Cleanse;
    }
    bool SameCondition(const FWarAbilityCondition& A,const FWarAbilityCondition& B)
    {
        if (A.Kind!=B.Kind || A.Subject!=B.Subject || A.Source!=B.Source || A.AbilityId!=B.AbilityId || A.EffectId!=B.EffectId
            || A.bNot!=B.bNot || A.Children.Num()!=B.Children.Num()) return false;
        for (int32 I=0;I<A.Children.Num();++I) if (!SameCondition(A.Children[I],B.Children[I])) return false;
        return true;
    }
    bool SameDefinition(const FWarAbilityDefinition& A,const FWarAbilityDefinition& B)
    {
        if (A.Id!=B.Id || A.Career!=B.Career || A.Shape!=B.Shape || A.School!=B.School || A.AssignmentId!=B.AssignmentId
            || A.TargetKind!=B.TargetKind || A.TimingMode!=B.TimingMode || A.Version!=B.Version || A.Name!=B.Name
            || A.Summary!=B.Summary || A.UnavailableReason!=B.UnavailableReason || A.ResourceLabel!=B.ResourceLabel
            || A.Slot!=B.Slot || A.UnlockLevel!=B.UnlockLevel || A.MaxTargets!=B.MaxTargets
            || A.bEnemyTarget!=B.bEnemyTarget || A.bSpendAll!=B.bSpendAll || A.bBlockedBySilence!=B.bBlockedBySilence
            || A.bLegacyTargeting!=B.bLegacyTargeting || A.bAuthoredTiming!=B.bAuthoredTiming || A.bCancelOnMovement!=B.bCancelOnMovement
            || A.PreparationScale!=B.PreparationScale || A.Range!=B.Range || A.Radius!=B.Radius || A.ProjectileSpeed!=B.ProjectileSpeed
            || A.Cooldown!=B.Cooldown || A.Gcd!=B.Gcd || A.Mana!=B.Mana || A.Build!=B.Build || A.Cost!=B.Cost
            || A.MinimumResource!=B.MinimumResource || A.ResourceMax!=B.ResourceMax || A.ResourceInitial!=B.ResourceInitial
            || A.ReleaseFraction!=B.ReleaseFraction || A.CastSeconds!=B.CastSeconds || A.ChannelSeconds!=B.ChannelSeconds
            || A.TickInterval!=B.TickInterval || A.Presentations.Num()!=B.Presentations.Num()
            || A.Effects.Num()!=B.Effects.Num() || A.Conditions.Num()!=B.Conditions.Num()) return false;
        for (const auto& Pair:A.Presentations) { const FName* Value=B.Presentations.Find(Pair.Key); if (!Value || *Value!=Pair.Value) return false; }
        for (int32 I=0;I<A.Effects.Num();++I) if (!SameEffect(A.Effects[I],B.Effects[I])) return false;
        for (int32 I=0;I<A.Conditions.Num();++I)
        {
            const auto& R=A.Conditions[I]; const auto& S=B.Conditions[I];
            if (R.Id!=S.Id || R.Event!=S.Event || R.Name!=S.Name || !SameCondition(R.Condition,S.Condition) || R.Actions.Num()!=S.Actions.Num()) return false;
            for (int32 J=0;J<R.Actions.Num();++J)
            { const auto& X=R.Actions[J]; const auto& Y=S.Actions[J]; if (X.Kind!=Y.Kind || X.EffectId!=Y.EffectId || X.Value!=Y.Value || !SameEffect(X.Effect,Y.Effect)) return false; }
        }
        return true;
    }
    TSharedPtr<FJsonObject> Parse(const FString& Text)
    { TSharedPtr<FJsonObject> Row; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Row); return Row; }
    bool Serialize(const TSharedPtr<FJsonObject>& Row,FString& Text,FString& Hash,FString& Error)
    {
        Text.Reset(); return FJsonSerializer::Serialize(Row.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text))
            && WarCitadelProofHash::Text(Text,Hash,Error);
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCampaignCombatDefinitionTest,"AegisWar.Foundation.CampaignCombatDefinition",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCampaignCombatDefinitionTest::RunTest(const FString& Parameters)
{
    const auto Original=AppliedDefinition(); FString Payload,Hash,Error; FWarAbilityDefinition Restored;
    if (!TestTrue(TEXT("Actual immutable native fields encode"),WarCampaignCombatDefinition::Encode(Original,Payload,Hash,Error)))
    { AddError(Error); return false; }
    TestTrue(TEXT("Applied Unicode and multiline text remain in the pure payload"),Payload.Contains(TEXT("\u00e9")) && Payload.Contains(TEXT("\u76fe")));
    TestTrue(TEXT("Exact immutable UTF-8 SHA decodes"),WarCampaignCombatDefinition::Decode(Payload,Hash,Restored,Error));
    TestTrue(TEXT("Every native field and nested effect/condition/action round-trips"),SameDefinition(Original,Restored));
    FString Again,AgainHash; TestTrue(TEXT("Restored definition re-encodes"),WarCampaignCombatDefinition::Encode(Restored,Again,AgainHash,Error));
    TestEqual(TEXT("Sorted presentation keys and exact float values retain identical bytes"),Again,Payload);
    TestEqual(TEXT("Round-trip retains the exact applied payload SHA"),AgainHash,Hash);
    FWarAbilityDefinition Sentinel=AppliedDefinition(); Sentinel.Version=TEXT("untouched-output");
    TestFalse(TEXT("Changing even whitespace without a new owning hash is rejected"),WarCampaignCombatDefinition::Decode(Payload+TEXT(" "),Hash,Sentinel,Error));
    TestEqual(TEXT("Rejected decoding does not replace the caller's prior definition"),Sentinel.Version,FString(TEXT("untouched-output")));
    TestFalse(TEXT("A forged SHA cannot substitute current catalog values"),WarCampaignCombatDefinition::Decode(Payload,FString::ChrN(64,TEXT('f')),Restored,Error));
    for (int32 Case=0;Case<10;++Case)
    {
        auto Row=Parse(Payload); FString Changed,ChangedHash;
        if (Case==0) Row->RemoveField(TEXT("resourceInitial"));
        if (Case==1) Row->SetStringField(TEXT("uobject"),TEXT("/Script/UnsafeEffect"));
        if (Case==2) Row->SetNumberField(TEXT("range"),-1);
        if (Case==3) Row->SetNumberField(TEXT("schemaVersion"),2);
        if (Case==4) Row->GetArrayField(TEXT("effects"))[0]->AsObject()->SetStringField(TEXT("id"),TEXT(""));
        if (Case==5) Row->GetArrayField(TEXT("conditions"))[0]->AsObject()->GetArrayField(TEXT("actions"))[0]->AsObject()
            ->GetObjectField(TEXT("effect"))->SetStringField(TEXT("label"),TEXT("hidden nondefault effect"));
        if (Case==6) Row->GetArrayField(TEXT("conditions"))[0]->AsObject()->GetArrayField(TEXT("actions"))[2]->AsObject()
            ->GetObjectField(TEXT("effect"))->SetStringField(TEXT("id"),TEXT("burn"));
        if (Case==7) Row->SetStringField(TEXT("cooldown"),TEXT("2"));
        if (Case==8) Row->SetNumberField(TEXT("name"),123);
        if (Case==9) Row->SetNumberField(TEXT("enemyTarget"),1);
        if (!TestTrue(TEXT("Tamper fixture independently hashes its actual changed bytes"),Serialize(Row,Changed,ChangedHash,Error))) return false;
        TestFalse(*FString::Printf(TEXT("Malformed immutable schema/semantics case %d rejects despite valid SHA"),Case),WarCampaignCombatDefinition::Decode(Changed,ChangedHash,Restored,Error));
    }
    auto Legacy=Original; Legacy.bLegacyTargeting=true; Legacy.Effects[0].Recipient=NAME_None; Legacy.Effects[1].Recipient=NAME_None;
    TestTrue(TEXT("Real legacy catalog effect IDs retain an empty recorded recipient"),WarCampaignCombatDefinition::Encode(Legacy,Again,AgainHash,Error));
    TestTrue(TEXT("Legacy immutable definition decodes without recipient substitution"),WarCampaignCombatDefinition::Decode(Again,AgainHash,Restored,Error));
    TestTrue(TEXT("Legacy original values are exactly preserved"),SameDefinition(Legacy,Restored));
    auto Handmade=Original; Handmade.Effects[0].Id=NAME_None;
    TestFalse(TEXT("Handmade status provenance cannot invent an applied effect ID"),WarCampaignCombatDefinition::Encode(Handmade,Again,AgainHash,Error));
    TestTrue(TEXT("Failed encoding clears stale bytes and SHA"),Again.IsEmpty() && AgainHash.IsEmpty());
    auto Recursive=Original; Recursive.Conditions[0].Event=TEXT("tick"); Recursive.Conditions[0].Actions[2].Effect.PeriodicDuration=2;
    TestFalse(TEXT("A tick bonus cannot introduce a recursive periodic scheduler"),WarCampaignCombatDefinition::Encode(Recursive,Again,AgainHash,Error));
    auto TooLarge=Original; TooLarge.Summary=FString::ChrN(4097,TEXT('x'));
    TestFalse(TEXT("Bounded text is enforced before admitting a complete character document"),WarCampaignCombatDefinition::Encode(TooLarge,Again,AgainHash,Error));
    return !HasAnyErrors();
}
#endif
