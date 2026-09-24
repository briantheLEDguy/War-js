#include "SWarAbilityWorkshop.h"
#include "WarAbilityWorkshopSubsystem.h"
#include "WarAbilityConditions.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarRuntimeSettings.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Framework/Application/SlateApplication.h"
#include "UObject/UObjectIterator.h"

using namespace WarWorkshopJson;
namespace
{
    FString FreshId(const TCHAR* Prefix) { return FString(Prefix)+FGuid::NewGuid().ToString(EGuidFormats::Digits); }
    TSharedPtr<FJsonObject> Predicate()
    { auto P=MakeShared<FJsonObject>(); P->SetStringField(TEXT("kind"),TEXT("hot")); P->SetStringField(TEXT("subject"),TEXT("recipient")); P->SetStringField(TEXT("source"),TEXT("self")); return P; }
    void Append(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key,const TSharedPtr<FJsonObject>& Value)
    { auto Values=Array(Parent,Key); Values.Add(MakeShared<FJsonValueObject>(Value)); Parent->SetArrayField(Key,Values); }
    void Remove(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key,const TSharedPtr<FJsonObject>& Value)
    { auto Values=Array(Parent,Key); Values.RemoveAll([&](const auto& V) { return V->AsObject()==Value; }); Parent->SetArrayField(Key,Values); }
}
TSharedRef<SWidget> SWarAbilityWorkshop::AbilityPicker(const FString& Id,TFunction<void(FString)> Action)
{
    const auto A=Store.IsValid() ? Find(Store->Document().Get(),TEXT("abilities"),Id) : nullptr;
    return SNew(SComboButton).ButtonContent()[Label(A ? Text(A,TEXT("name")) : TEXT("Choose ability…"))].OnGetMenuContent_Lambda([this,Action] {
        auto Menu=SNew(SVerticalBox),Matches=SNew(SVerticalBox);
        auto RefreshMatches=[this,Matches,Action](const FText& Query) { Matches->ClearChildren(); if (!Store.IsValid()) return; int32 Count=0;
            for (const auto& V:Array(Store->Document().Get(),TEXT("abilities"))) { const auto A=V->AsObject(); if (!(Text(A,TEXT("name"))+TEXT(" ")+Text(A,TEXT("summary"))).Contains(Query.ToString())) continue;
                Matches->AddSlot().AutoHeight().Padding(0,3)[Button(Text(A,TEXT("name")),[Action,Id=Text(A,TEXT("id"))] { FSlateApplication::Get().DismissAllMenus(); Action(Id); })];
                Matches->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Text(A,TEXT("summary")))).Font(FCoreStyle::GetDefaultFontStyle("Regular",14)).AutoWrapText(true)]; if (++Count>=100) break; }
            if (Count==100) Matches->AddSlot().AutoHeight()[Label(TEXT("Showing 100 matches. Type to narrow results."),true)]; };
        Menu->AddSlot().AutoHeight()[SNew(SSearchBox).HintText(FText::FromString(TEXT("Find ability by name or description"))).OnTextChanged_Lambda(RefreshMatches)];
        Menu->AddSlot().FillHeight(1)[SNew(SScrollBox)+SScrollBox::Slot()[Matches]]; RefreshMatches(FText::GetEmpty());
        return SNew(SBox).WidthOverride(450).HeightOverride(450)[Menu]; });
}
TSharedRef<SWidget> SWarAbilityWorkshop::EffectPicker(const FString& AbilityId,const FString& Id,TFunction<void(FString)> Action)
{
    const auto A=Composer && Text(Composer,TEXT("id"))==AbilityId ? Composer : Store.IsValid() ? Find(Store->Document().Get(),TEXT("abilities"),AbilityId) : nullptr;
    const auto Description=[](const TSharedPtr<FJsonObject>& E) { const auto Status=Object(E,Text(E,TEXT("kind"))==TEXT("player_status") ? TEXT("playerStatus") : TEXT("status")); return Text(E,TEXT("kind"))+TEXT(" · ")+Text(E,TEXT("recipient"))+TEXT(" · ")+(Status ? Text(Status,TEXT("label")) : Text(E,TEXT("id"))); };
    TArray<TSharedPtr<FJsonObject>> Effects; for (const auto& V:Array(A,TEXT("effects"))) Effects.Add(V->AsObject());
    for (const auto& R:Array(A,TEXT("conditions"))) for (const auto& V:Array(R->AsObject(),TEXT("actions"))) if (Text(V->AsObject(),TEXT("kind"))==TEXT("add_effect")) Effects.Add(Object(V->AsObject(),TEXT("effect")));
    const auto* Selected=Effects.FindByPredicate([&](const auto& E) { return Text(E,TEXT("id"))==Id; });
    return SNew(SComboButton).ButtonContent()[Label(Selected ? Description(*Selected) : TEXT("Choose effect…"))].OnGetMenuContent_Lambda([this,Effects,Description,Action] {
        auto Menu=SNew(SVerticalBox),Matches=SNew(SVerticalBox);
        auto Search=[this,Effects,Description,Action,Matches](const FText& Query) { Matches->ClearChildren();
            for (const auto& E:Effects) { const FString LabelText=Description(E); if (!(LabelText+TEXT(" ")+Text(E,TEXT("id"))).Contains(Query.ToString())) continue;
                Matches->AddSlot().AutoHeight().Padding(0,3)[Button(LabelText,[Action,EffectId=Text(E,TEXT("id"))] { FSlateApplication::Get().DismissAllMenus(); Action(EffectId); })]; } };
        Menu->AddSlot().AutoHeight()[SNew(SSearchBox).HintText(FText::FromString(TEXT("Find effect by type, name or identity"))).OnTextChanged_Lambda(Search)];
        Menu->AddSlot().FillHeight(1)[SNew(SScrollBox)+SScrollBox::Slot()[Matches]]; Search(FText::GetEmpty()); return SNew(SBox).WidthOverride(450).HeightOverride(350)[Menu]; });
}
void SWarAbilityWorkshop::SetComposer(const FString& AbilityId,const FString& AssignmentId)
{
    if (!Store.IsValid()) return;
    SelectedAbility=AbilityId; SelectedAssignment=AssignmentId; Composer=Clone(Find(Store->Document().Get(),TEXT("abilities"),AbilityId)); bDirtyComposer=false; BuildInspector();
}
void SWarAbilityWorkshop::MarkComposer(bool Rebuild) { bDirtyComposer=true; Notice=TEXT("Inspector changes are uncommitted. Apply validates the shared ability and every class override."); if (Rebuild) BuildInspector(); }
void SWarAbilityWorkshop::ApplyComposer()
{
    if (!Composer || !Store.IsValid()) return; const auto W=Clone(Store->Document().Get());
    auto Abilities=Array(W,TEXT("abilities")); const int32 Index=Abilities.IndexOfByPredicate([this](const auto& V) { return Text(V->AsObject(),TEXT("id"))==SelectedAbility; });
    if (Index!=INDEX_NONE && Serialize(Object(Composer,TEXT("timing")))!=Serialize(Object(Abilities[Index]->AsObject(),TEXT("timing")))) Composer->SetBoolField(TEXT("authoredTiming"),true);
    if (Index==INDEX_NONE) Abilities.Add(MakeShared<FJsonValueObject>(Clone(Composer))); else Abilities[Index]=MakeShared<FJsonValueObject>(Clone(Composer)); W->SetArrayField(TEXT("abilities"),Abilities);
    FString Error; if (!Store->Document().Commit(W,Error)) { Notice=TEXT("Invalid · ")+Error; return; }
    bDirtyComposer=false; Notice=TEXT("Shared base updated. Compatible class overrides remain in place."); Changed();
}
void SWarAbilityWorkshop::NewAbility(bool Duplicate)
{
    if (!Store.IsValid()) return;
    if (bDirtyComposer) { Notice=TEXT("Apply or discard the current inspector changes first."); return; }
    auto Source=Duplicate ? Composer : (Array(Store->Document().Get(),TEXT("abilities")).IsEmpty() ? nullptr : Array(Store->Document().Get(),TEXT("abilities"))[0]->AsObject());
    if (!Source) return;
    Composer=Clone(Source); SelectedAbility=FreshId(TEXT("workshop.")); SelectedAssignment.Reset(); Composer->SetStringField(TEXT("id"),SelectedAbility);
    Composer->SetStringField(TEXT("name"),Duplicate ? Text(Source,TEXT("name"))+TEXT(" copy") : TEXT("New ability")); Composer->SetBoolField(TEXT("archived"),false);
    if (!Duplicate)
    {
        Composer->SetStringField(TEXT("summary"),TEXT("Describe the ability.")); Composer->RemoveField(TEXT("unavailableReason")); Composer->SetBoolField(TEXT("legacyTargeting"),false);
        Composer->SetArrayField(TEXT("effects"),{MakeShared<FJsonValueObject>(DefaultEffect(TEXT("damage")))}); Composer->SetArrayField(TEXT("conditions"),{});
        auto Target=Parse(TEXT("{\"target\":\"enemy\",\"shape\":\"beam\",\"range\":20,\"radius\":0,\"maxTargets\":1}")); Composer->SetObjectField(TEXT("targeting"),Target);
        Composer->SetObjectField(TEXT("resource"),Parse(TEXT("{\"manaCost\":0,\"careerCost\":0,\"careerBuild\":0}")));
        Composer->SetObjectField(TEXT("timing"),Parse(TEXT("{\"mode\":\"cast\",\"castSec\":0.5}"))); Composer->SetNumberField(TEXT("cooldownSec"),3); Composer->SetNumberField(TEXT("gcdSec"),1.5);
    }
    // New identities do not carry class bindings; assignment admission checks presentation compatibility.
    Section=TEXT("Basics"); bInspector=true; bDirtyComposer=true; BuildInspector();
}
void SWarAbilityWorkshop::AssignToClass(const FString& ClassId)
{
    if (!Store.IsValid() || !Composer) return;
    if (bDirtyComposer) { Notice=TEXT("Apply the shared ability before assigning it."); return; }
    const auto W=Clone(Store->Document().Get()); auto Assignment=Parse(TEXT("{\"unlockLevel\":1,\"displayOrder\":100,\"presentations\":{},\"overrides\":[]}"));
    Assignment->SetStringField(TEXT("id"),FreshId(TEXT("assignment."))); Assignment->SetStringField(TEXT("abilityId"),SelectedAbility); Assignment->SetStringField(TEXT("classId"),ClassId);
    Append(W,TEXT("assignments"),Assignment); FString Error; if (!Store->Document().Commit(W,Error)) { Notice=Error; return; }
    SelectedAssignment=Text(Assignment,TEXT("id")); Notice=TEXT("Class assignment added at level 1. Configure unlock and approved presentation bindings."); Changed();
}
TSharedPtr<FJsonObject> SWarAbilityWorkshop::DefaultEffect(const FString& Kind) const
{
    auto E=MakeShared<FJsonObject>(); const FString Id=FreshId(TEXT("effect.")); E->SetStringField(TEXT("id"),Id); E->SetStringField(TEXT("kind"),Kind); E->SetStringField(TEXT("recipient"),Kind==TEXT("heal") || Kind==TEXT("player_status") || Kind==TEXT("movement") || Kind==TEXT("cleanse") ? TEXT("caster") : TEXT("target"));
    if (Kind==TEXT("damage") || Kind==TEXT("heal")) { E->SetObjectField(TEXT("amount"),Parse(TEXT("{\"min\":10,\"max\":10,\"statScale\":0,\"levelScale\":0,\"resourceScale\":0}"))); E->SetStringField(TEXT("school"),TEXT("physical")); }
    else if (Kind==TEXT("status") || Kind==TEXT("player_status")) { auto Status=Parse(TEXT("{\"durationSec\":5,\"magnitude\":0.25}")); Status->SetStringField(TEXT("id"),Id); Status->SetStringField(TEXT("kind"),Kind==TEXT("status") ? TEXT("slow") : TEXT("shield")); Status->SetStringField(TEXT("label"),Kind==TEXT("status") ? TEXT("Slow") : TEXT("Shield")); E->SetObjectField(Kind==TEXT("status") ? TEXT("status") : TEXT("playerStatus"),Status); if (Kind==TEXT("player_status")) E->SetObjectField(TEXT("amount"),Parse(TEXT("{\"min\":10,\"max\":10}"))); }
    else if (Kind==TEXT("movement")) E->SetObjectField(TEXT("movement"),Parse(TEXT("{\"mode\":\"forward\",\"distance\":3}")));
    else if (Kind==TEXT("cleanse")) E->SetObjectField(TEXT("cleanse"),Parse(TEXT("{\"kinds\":[\"slow\",\"root\"]}")));
    return E;
}
void SWarAbilityWorkshop::BuildInspector()
{
    if (!Inspector) return; Inspector->ClearChildren();
    if (!Composer) { Inspector->AddSlot().AutoHeight()[Label(TEXT("Select an ability or create a new one."),true)]; return; }
    Inspector->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Text(Composer,TEXT("name")))).Font(FCoreStyle::GetDefaultFontStyle("Bold",20)).AutoWrapText(true)];
    Inspector->AddSlot().AutoHeight().Padding(0,6)[Label(TEXT("SHARED BASE · structural composer"),true)];
    auto Actions=SNew(SHorizontalBox); Actions->AddSlot().FillWidth(1)[Button(TEXT("Apply"),[this] { ApplyComposer(); })];
    Actions->AddSlot().FillWidth(1).Padding(5,0)[Button(TEXT("Discard"),[this] { SetComposer(SelectedAbility,SelectedAssignment); })];
    Actions->AddSlot().FillWidth(1)[Button(TEXT("Copy"),[this] { NewAbility(true); })]; Inspector->AddSlot().AutoHeight()[Actions];
    TArray<TPair<FString,FString>> Sections; for (const FString S:{TEXT("Basics"),TEXT("Targeting"),TEXT("Effects"),TEXT("Conditions"),TEXT("Costs & Timing"),TEXT("Presentation"),TEXT("Class Assignments")}) Sections.Add({S,S});
    Inspector->AddSlot().AutoHeight().Padding(0,12)[Choice(Section,Sections,[this](FString S) { Section=S; BuildInspector(); })];
    const auto A=Composer;
    if (Section==TEXT("Basics"))
    {
        Inspector->AddSlot().AutoHeight()[Field(TEXT("Name"),Text(A,TEXT("name")),[this,A](FString V) { A->SetStringField(TEXT("name"),V); MarkComposer(); })];
        Inspector->AddSlot().AutoHeight()[Field(TEXT("Description"),Text(A,TEXT("summary")),[this,A](FString V) { A->SetStringField(TEXT("summary"),V); MarkComposer(); })];
        bool Archived=false; A->TryGetBoolField(TEXT("archived"),Archived);
        Inspector->AddSlot().AutoHeight().Padding(0,12)[SNew(SCheckBox).IsChecked(Archived ? ECheckBoxState::Checked : ECheckBoxState::Unchecked).OnCheckStateChanged_Lambda([this,A](ECheckBoxState V) { A->SetBoolField(TEXT("archived"),V==ECheckBoxState::Checked); MarkComposer(); })[Label(TEXT("Archived (unavailable for new casts)"))]];
        Inspector->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("Identity stays stable through renames. Archiving removes active assignments on the next deployment; saved hotbar entries remain visible and disabled."))).AutoWrapText(true)];
    }
    else if (Section==TEXT("Targeting"))
    {
        const auto T=Object(A,TEXT("targeting"));
        Inspector->AddSlot().AutoHeight()[Label(TEXT("Selected target"),true)];
        Inspector->AddSlot().AutoHeight()[Choice(Text(T,TEXT("target")),{{TEXT("self"),TEXT("Self")},{TEXT("ally"),TEXT("Ally")},{TEXT("enemy"),TEXT("Enemy")},{TEXT("ground"),TEXT("Ground")}},[this,A,T](FString V) { T->SetStringField(TEXT("target"),V); A->SetBoolField(TEXT("legacyTargeting"),false); MarkComposer(); })];
        Inspector->AddSlot().AutoHeight().Padding(0,8)[Choice(Text(T,TEXT("shape")),{{TEXT("melee"),TEXT("Melee")},{TEXT("beam"),TEXT("Direct / beam")},{TEXT("projectile"),TEXT("Projectile")},{TEXT("area"),TEXT("Area")},{TEXT("cone"),TEXT("Cone")},{TEXT("self"),TEXT("Self")},{TEXT("dash"),TEXT("Validated movement")}},[this,A,T](FString V) { T->SetStringField(TEXT("shape"),V); A->SetBoolField(TEXT("legacyTargeting"),false); MarkComposer(); })];
        for (const auto& Pair:TArray<TPair<FString,FString>>{{TEXT("range"),TEXT("Range (m)")},{TEXT("radius"),TEXT("Radius (m)")},{TEXT("maxTargets"),TEXT("Maximum recipients")},{TEXT("projectileSpeed"),TEXT("Projectile speed (m/s)")}})
            Inspector->AddSlot().AutoHeight()[NumericField(Pair.Value,Number(T,*Pair.Key,Pair.Key==TEXT("maxTargets") ? 1 : Pair.Key==TEXT("projectileSpeed") ? 20 : 0),[this,T,K=Pair.Key](double V) { T->SetNumberField(K,V); MarkComposer(); })];
    }
    else if (Section==TEXT("Effects"))
    {
        for (const auto& V:Array(A,TEXT("effects")))
        {
            const auto E=V->AsObject(); auto Box=SNew(SVerticalBox); BuildEffect(Box,E);
            auto Controls=SNew(SHorizontalBox);
            Controls->AddSlot().FillWidth(1)[Button(TEXT("Move up"),[this,A,E] { auto Values=Array(A,TEXT("effects")); const int32 I=Values.IndexOfByPredicate([&](const auto& X) { return X->AsObject()==E; }); if (I>0) Values.Swap(I,I-1); A->SetArrayField(TEXT("effects"),Values); MarkComposer(true); })];
            Controls->AddSlot().FillWidth(1)[Button(TEXT("Remove effect"),[this,A,E] { Remove(A,TEXT("effects"),E); MarkComposer(true); })]; Box->AddSlot().AutoHeight().Padding(0,8)[Controls];
            Inspector->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(SBorder).Padding(10)[Box]];
        }
        Inspector->AddSlot().AutoHeight()[Button(TEXT("+ Add effect"),[this,A] { Append(A,TEXT("effects"),DefaultEffect(TEXT("damage"))); MarkComposer(true); })];
    }
    else if (Section==TEXT("Conditions"))
    {
        Inspector->AddSlot().AutoHeight().Padding(0,0,0,10)[SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(TEXT("All matching rules apply. Presence checks do not consume effects. Each event reads one snapshot before any effects apply.")))];
        for (const auto& V:Array(A,TEXT("conditions"))) { auto Box=SNew(SVerticalBox); BuildRule(Box,V->AsObject()); Inspector->AddSlot().AutoHeight().Padding(0,0,0,12)[SNew(SBorder).Padding(10)[Box]]; }
        Inspector->AddSlot().AutoHeight()[Button(TEXT("+ Add IF → THEN rule"),[this,A] {
            auto R=Parse(TEXT("{\"event\":\"application\",\"name\":\"Conditional bonus\",\"condition\":{\"kind\":\"all\",\"children\":[]},\"actions\":[]}")); R->SetStringField(TEXT("id"),FreshId(TEXT("rule."))); Append(Object(R,TEXT("condition")),TEXT("children"),Predicate());
            auto Action=Parse(TEXT("{\"kind\":\"add_effect\"}")); Action->SetObjectField(TEXT("effect"),DefaultEffect(TEXT("player_status"))); Append(R,TEXT("actions"),Action); Append(A,TEXT("conditions"),R); MarkComposer(true); })];
    }
    else if (Section==TEXT("Costs & Timing"))
    {
        const auto T=Object(A,TEXT("timing")),R=Object(A,TEXT("resource"));
        Inspector->AddSlot().AutoHeight()[Choice(Text(T,TEXT("mode")),{{TEXT("instant"),TEXT("Instant")},{TEXT("cast"),TEXT("Cast")},{TEXT("channel"),TEXT("Channel")}},[this,T](FString V) { T->SetStringField(TEXT("mode"),V); if (V==TEXT("channel")) { T->SetNumberField(TEXT("channelSec"),3); T->SetNumberField(TEXT("intervalSec"),1); } MarkComposer(true); })];
        for (const TCHAR* K:{TEXT("castSec"),TEXT("channelSec"),TEXT("intervalSec")}) Inspector->AddSlot().AutoHeight()[NumericField(FString(K)+TEXT(" (s)"),Number(T,K),[this,T,K](double V) { T->SetNumberField(K,V); MarkComposer(); })];
        for (const TCHAR* K:{TEXT("cooldownSec"),TEXT("gcdSec")}) Inspector->AddSlot().AutoHeight()[NumericField(FString(K)+TEXT(" (s)"),Number(A,K),[this,A,K](double V) { A->SetNumberField(K,V); MarkComposer(); })];
        for (const TCHAR* K:{TEXT("manaCost"),TEXT("careerCost"),TEXT("careerBuild"),TEXT("minCareer")}) Inspector->AddSlot().AutoHeight()[NumericField(K,Number(R,K),[this,R,K](double V) { R->SetNumberField(K,V); MarkComposer(); })];
    }
    else if (Section==TEXT("Presentation"))
    {
        Inspector->AddSlot().AutoHeight()[SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(TEXT("Bindings belong to the selected class assignment. Choose an admitted recipe per character profile. Every animation role must be available before activation.")))];
        const auto Assignment=Store.IsValid() ? Find(Store->Document().Get(),TEXT("assignments"),SelectedAssignment) : nullptr;
        if (!Assignment) Inspector->AddSlot().AutoHeight().Padding(0,12)[Label(TEXT("Select a class assignment first."),true)];
        auto Profiles=GetDefault<UWarRuntimeSettings>()->PlayableRoster;
        Profiles.AddUnique(GetDefault<UWarRuntimeSettings>()->AegisDevelopmentVisual);
        Profiles.AddUnique(GetDefault<UWarRuntimeSettings>()->RiftboundDevelopmentVisual);
        if (Assignment) for (const auto& ProfileAsset:Profiles)
        {
            const auto* It=ProfileAsset.LoadSynchronous();
            if (!It || It->ClassId.ToString()!=Text(Assignment,TEXT("classId"))) continue;
            TArray<TPair<FString,FString>> Recipes; for (const auto& Pair:It->AbilityPresentations) Recipes.Add({Pair.Key.ToString(),Pair.Key.ToString()});
            const FString Profile=It->ProfileKey.ToString(); Inspector->AddSlot().AutoHeight().Padding(0,8)[Label(Profile)];
            Inspector->AddSlot().AutoHeight()[Choice(Text(Object(Assignment,TEXT("presentations")),*Profile),Recipes,[this,Profile](FString Recipe) {
                const auto W=Clone(Store->Document().Get()),Assignment=Find(W,TEXT("assignments"),SelectedAssignment); if (!Assignment) return;
                Object(Assignment,TEXT("presentations"))->SetStringField(Profile,Recipe); FString Error; if (!Store->Document().Commit(W,Error)) Notice=Error; else Changed(); })];
        }
    }
    else
    {
        if (!Store.IsValid()) return; const auto W=Store->Document().Get(); TArray<TPair<FString,FString>> ClassChoices;
        for (const auto& C:Array(W,TEXT("classes"))) ClassChoices.Add({Text(C->AsObject(),TEXT("id")),Text(C->AsObject(),TEXT("name"))});
        Inspector->AddSlot().AutoHeight()[Choice(TEXT("Assign to class…"),ClassChoices,[this](FString C) { AssignToClass(C); })];
        for (const auto& V:Array(W,TEXT("assignments")))
        {
            const auto Assignment=V->AsObject(); if (Text(Assignment,TEXT("abilityId"))!=SelectedAbility) continue; const FString Id=Text(Assignment,TEXT("id"));
            Inspector->AddSlot().AutoHeight().Padding(0,12)[Label(Text(Find(W,TEXT("classes"),Text(Assignment,TEXT("classId"))),TEXT("name")))];
            for (const TCHAR* K:{TEXT("unlockLevel"),TEXT("displayOrder")}) Inspector->AddSlot().AutoHeight()[NumericField(K,Number(Assignment,K),[this,Id,K](double Value) { const auto Candidate=Clone(Store->Document().Get()); Find(Candidate,TEXT("assignments"),Id)->SetNumberField(K,Value); FString Error; if (!Store->Document().Commit(Candidate,Error)) Notice=Error; else Changed(); })];
            Inspector->AddSlot().AutoHeight()[Button(TEXT("Select bindings / overrides"),[this,Id] { SelectedAssignment=Id; Section=TEXT("Presentation"); BuildInspector(); })];
            Inspector->AddSlot().AutoHeight()[Button(TEXT("Remove assignment"),[this,Id] { const auto Candidate=Clone(Store->Document().Get()); Remove(Candidate,TEXT("assignments"),Find(Candidate,TEXT("assignments"),Id)); FString Error; if (!Store->Document().Commit(Candidate,Error)) Notice=Error; else Changed(); })];
        }
    }
}
void SWarAbilityWorkshop::BuildEffect(const TSharedRef<SVerticalBox>& Box,const TSharedPtr<FJsonObject>& E,bool Bonus)
{
    TArray<TPair<FString,FString>> Kinds{{TEXT("damage"),TEXT("Damage")},{TEXT("heal"),TEXT("Healing")},{TEXT("status"),TEXT("Debuff / crowd control")},{TEXT("player_status"),TEXT("Shield / buff")}};
    if (!Bonus) { Kinds.Add({TEXT("cleanse"),TEXT("Cleanse")}); Kinds.Add({TEXT("movement"),TEXT("Validated movement")}); }
    Box->AddSlot().AutoHeight()[Choice(Text(E,TEXT("kind")),Kinds,[this,E](FString Kind) { const FString Id=Text(E,TEXT("id")); E->Values=DefaultEffect(Kind)->Values; E->SetStringField(TEXT("id"),Id); MarkComposer(true); })];
    Box->AddSlot().AutoHeight().Padding(0,8)[Choice(Text(E,TEXT("recipient")),{{TEXT("caster"),TEXT("Caster")},{TEXT("target"),TEXT("Selected target / current recipient")},{TEXT("allies"),TEXT("Allied recipients")},{TEXT("enemies"),TEXT("Enemy recipients")}},[this,E](FString V) { E->SetStringField(TEXT("recipient"),V); Composer->SetBoolField(TEXT("legacyTargeting"),false); MarkComposer(); })];
    const auto Amount=Object(E,TEXT("amount")); if (Amount) for (const auto& Pair:TArray<TPair<FString,FString>>{{TEXT("min"),TEXT("Minimum amount")},{TEXT("max"),TEXT("Maximum amount")},{TEXT("statScale"),TEXT("Stat scaling")},{TEXT("levelScale"),TEXT("Level scaling")},{TEXT("resourceScale"),TEXT("Resource scaling")}})
        Box->AddSlot().AutoHeight()[NumericField(Pair.Value,Number(Amount,*Pair.Key),[this,Amount,K=Pair.Key](double V) { Amount->SetNumberField(K,V); MarkComposer(); })];
    if (Text(E,TEXT("kind"))==TEXT("damage")) Box->AddSlot().AutoHeight().Padding(0,8)[Choice(Text(E,TEXT("school")),{{TEXT("physical"),TEXT("Physical")},{TEXT("fire"),TEXT("Fire")},{TEXT("spirit"),TEXT("Spirit")},{TEXT("elemental"),TEXT("Elemental")}},[this,E](FString V) { E->SetStringField(TEXT("school"),V); MarkComposer(); })];
    if (Text(E,TEXT("kind"))==TEXT("damage") || Text(E,TEXT("kind"))==TEXT("heal"))
    {
        const auto Periodic=Object(E,TEXT("periodic"));
        Box->AddSlot().AutoHeight().Padding(0,8)[SNew(SCheckBox).IsChecked(Periodic ? ECheckBoxState::Checked : ECheckBoxState::Unchecked).OnCheckStateChanged_Lambda([this,E](ECheckBoxState V) { if (V==ECheckBoxState::Checked) E->SetObjectField(TEXT("periodic"),Parse(TEXT("{\"durationSec\":6,\"intervalSec\":2}"))); else E->RemoveField(TEXT("periodic")); MarkComposer(true); })[Label(TEXT("Periodic (HoT / DoT)"))]];
        if (Periodic) for (const TCHAR* K:{TEXT("durationSec"),TEXT("intervalSec")}) Box->AddSlot().AutoHeight()[NumericField(FString(K)+TEXT(" (s)"),Number(Periodic,K),[this,Periodic,K](double V) { Periodic->SetNumberField(K,V); MarkComposer(); })];
    }
    const auto Status=Object(E,Text(E,TEXT("kind"))==TEXT("status") ? TEXT("status") : TEXT("playerStatus"));
    if (Status)
    {
        TArray<TPair<FString,FString>> Choices; const TArray<FString> Values=Text(E,TEXT("kind"))==TEXT("status") ? TArray<FString>{TEXT("slow"),TEXT("root"),TEXT("silence"),TEXT("stagger"),TEXT("mark"),TEXT("debuff"),TEXT("burn"),TEXT("bleed")} : TArray<FString>{TEXT("shield"),TEXT("guard"),TEXT("empower"),TEXT("haste")}; for (const FString& V:Values) Choices.Add({V,V});
        Box->AddSlot().AutoHeight()[Choice(Text(Status,TEXT("kind")),Choices,[this,Status](FString V) { Status->SetStringField(TEXT("kind"),V); MarkComposer(true); })];
        Box->AddSlot().AutoHeight()[Field(TEXT("Status name"),Text(Status,TEXT("label")),[this,Status](FString V) { Status->SetStringField(TEXT("label"),V); MarkComposer(); })];
        Box->AddSlot().AutoHeight()[NumericField(TEXT("Duration (s)"),Number(Status,TEXT("durationSec")),[this,Status](double V) { Status->SetNumberField(TEXT("durationSec"),V); MarkComposer(); })];
        Box->AddSlot().AutoHeight()[NumericField(TEXT("Magnitude (fraction, 0.25 = 25%)"),Number(Status,TEXT("magnitude")),[this,Status](double V) { Status->SetNumberField(TEXT("magnitude"),V); MarkComposer(); })];
    }
    const auto Movement=Object(E,TEXT("movement")); if (Movement)
    {
        Box->AddSlot().AutoHeight()[Choice(Text(Movement,TEXT("mode")),{{TEXT("forward"),TEXT("Forward")},{TEXT("backward"),TEXT("Backward")},{TEXT("toward_target"),TEXT("Toward target")}},[this,Movement](FString V) { Movement->SetStringField(TEXT("mode"),V); MarkComposer(); })];
        Box->AddSlot().AutoHeight()[NumericField(TEXT("Distance (m, max 12)"),Number(Movement,TEXT("distance")),[this,Movement](double V) { Movement->SetNumberField(TEXT("distance"),V); MarkComposer(); })];
    }
    const auto Cleanse=Object(E,TEXT("cleanse")); if (Cleanse) for (const FString Kind:{TEXT("slow"),TEXT("root"),TEXT("stagger"),TEXT("debuff")})
        Box->AddSlot().AutoHeight()[SNew(SCheckBox).IsChecked(Array(Cleanse,TEXT("kinds")).ContainsByPredicate([&](const auto& V) { return V->AsString()==Kind; }) ? ECheckBoxState::Checked : ECheckBoxState::Unchecked)
            .OnCheckStateChanged_Lambda([this,Cleanse,Kind](ECheckBoxState V) { auto Values=Array(Cleanse,TEXT("kinds")); Values.RemoveAll([&](const auto& X) { return X->AsString()==Kind; }); if (V==ECheckBoxState::Checked) Values.Add(MakeShared<FJsonValueString>(Kind)); Cleanse->SetArrayField(TEXT("kinds"),Values); MarkComposer(); })[Label(Kind)]];
}
void SWarAbilityWorkshop::BuildCondition(const TSharedRef<SVerticalBox>& Box,const TSharedPtr<FJsonObject>& Node,const FString& Event,int32 Depth)
{
    const FString Kind=Text(Node,TEXT("kind"));
    if (Kind==TEXT("all") || Kind==TEXT("any"))
    {
        Box->AddSlot().AutoHeight()[Choice(Kind,{{TEXT("all"),TEXT("ALL of these conditions")},{TEXT("any"),TEXT("ANY of these conditions")}},[this,Node](FString V) { Node->SetStringField(TEXT("kind"),V); MarkComposer(); })];
        for (const auto& V:Array(Node,TEXT("children")))
        { auto Child=SNew(SVerticalBox); const auto C=V->AsObject(); BuildCondition(Child,C,Event,Depth+1); Child->AddSlot().AutoHeight().Padding(0,6)[Button(TEXT("Remove check"),[this,Node,C] { Remove(Node,TEXT("children"),C); MarkComposer(true); })]; Box->AddSlot().AutoHeight().Padding(Depth*5,8,0,8)[SNew(SBorder).Padding(8)[Child]]; }
        auto Add=SNew(SHorizontalBox); Add->AddSlot().FillWidth(1)[Button(TEXT("+ Check"),[this,Node,Event] { auto P=Predicate(); if (Event==TEXT("cast_start")) P->SetStringField(TEXT("subject"),TEXT("target")); Append(Node,TEXT("children"),P); MarkComposer(true); })];
        if (Depth==1) Add->AddSlot().FillWidth(1).Padding(4,0)[Button(TEXT("+ Group"),[this,Node,Event] { auto G=Parse(TEXT("{\"kind\":\"any\",\"children\":[]}")); auto P=Predicate(); if (Event==TEXT("cast_start")) P->SetStringField(TEXT("subject"),TEXT("target")); Append(G,TEXT("children"),P); Append(Node,TEXT("children"),G); MarkComposer(true); })];
        Box->AddSlot().AutoHeight()[Add];
        return;
    }
    TArray<TPair<FString,FString>> Subjects{{TEXT("caster"),TEXT("Caster")},{TEXT("target"),TEXT("Selected target")}}; if (Event!=TEXT("cast_start")) Subjects.Add({TEXT("recipient"),TEXT("Effect recipient")});
    Box->AddSlot().AutoHeight()[Choice(Text(Node,TEXT("subject")),Subjects,[this,Node](FString V) { Node->SetStringField(TEXT("subject"),V); MarkComposer(); })];
    bool Not=false; Node->TryGetBoolField(TEXT("not"),Not); Box->AddSlot().AutoHeight().Padding(0,5)[Choice(Not ? TEXT("not") : TEXT("is"),{{TEXT("is"),TEXT("IS / has")},{TEXT("not"),TEXT("IS NOT / does not have")}},[this,Node](FString V) { Node->SetBoolField(TEXT("not"),V==TEXT("not")); MarkComposer(); })];
    Box->AddSlot().AutoHeight()[Choice(Kind,{{TEXT("ability_effect"),TEXT("Active effect from an ability")},{TEXT("effect"),TEXT("Specific effect from an ability")},{TEXT("hot"),TEXT("A healing-over-time effect")},{TEXT("dot"),TEXT("A damage-over-time effect")},{TEXT("casting"),TEXT("Casting / channeling an ability")}},[this,Node](FString V) { Node->SetStringField(TEXT("kind"),V); MarkComposer(true); })];
    if (Kind==TEXT("ability_effect") || Kind==TEXT("effect") || Kind==TEXT("casting"))
    {
        Box->AddSlot().AutoHeight().Padding(0,5)[AbilityPicker(Text(Node,TEXT("abilityId")),[this,Node](FString V) { Node->SetStringField(TEXT("abilityId"),V); Node->RemoveField(TEXT("effectId")); MarkComposer(true); })];
        if (Kind==TEXT("effect")) Box->AddSlot().AutoHeight()[EffectPicker(Text(Node,TEXT("abilityId")),Text(Node,TEXT("effectId")),[this,Node](FString V) { Node->SetStringField(TEXT("effectId"),V); MarkComposer(true); })];
    }
    if (Kind!=TEXT("casting")) Box->AddSlot().AutoHeight().Padding(0,5)[Choice(Text(Node,TEXT("source")),{{TEXT("self"),TEXT("Applied by this caster")},{TEXT("allied"),TEXT("Applied by any allied caster")},{TEXT("any"),TEXT("Applied by any caster")}},[this,Node](FString V) { Node->SetStringField(TEXT("source"),V); MarkComposer(); })];
}
void SWarAbilityWorkshop::BuildRule(const TSharedRef<SVerticalBox>& Box,const TSharedPtr<FJsonObject>& Rule)
{
    Box->AddSlot().AutoHeight()[SNew(SEditableTextBox).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).Text(FText::FromString(Text(Rule,TEXT("name")))).OnTextCommitted_Lambda([this,Rule](const FText& V,ETextCommit::Type Type) { if (Type!=ETextCommit::OnCleared) { Rule->SetStringField(TEXT("name"),V.ToString()); MarkComposer(); } })];
    Box->AddSlot().AutoHeight().Padding(0,8)[SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,6,0)[Label(TEXT("AT"),true)]
        +SHorizontalBox::Slot().FillWidth(1)[Choice(Text(Rule,TEXT("event")),{{TEXT("cast_start"),TEXT("Cast start")},{TEXT("application"),TEXT("Impact / application")},{TEXT("tick"),TEXT("Each periodic tick")}},[this,Rule](FString V) { Rule->SetStringField(TEXT("event"),V); MarkComposer(true); })]];
    Box->AddSlot().AutoHeight().Padding(0,3)[Label(TEXT("IF"))]; BuildCondition(Box,Object(Rule,TEXT("condition")),Text(Rule,TEXT("event")),1);
    Box->AddSlot().AutoHeight().Padding(0,6)[Label(TEXT("THEN"))];
    for (const auto& V:Array(Rule,TEXT("actions")))
    {
        const auto Action=V->AsObject(); auto ActionBox=SNew(SVerticalBox); const FString Kind=Text(Action,TEXT("kind"));
        ActionBox->AddSlot().AutoHeight()[Choice(Kind,{{TEXT("flat"),TEXT("Add flat damage / healing")},{TEXT("percent"),TEXT("Change damage / healing by %")},{TEXT("add_effect"),TEXT("Add an effect")}},[this,Action](FString V) {
            Action->Values.Reset(); Action->SetStringField(TEXT("kind"),V);
            if (V==TEXT("add_effect")) Action->SetObjectField(TEXT("effect"),DefaultEffect(TEXT("player_status"))); else { Action->SetNumberField(TEXT("value"),V==TEXT("percent") ? .25 : 10); for (const auto& E:Array(Composer,TEXT("effects"))) if (Object(E->AsObject(),TEXT("amount"))) { Action->SetStringField(TEXT("effectId"),Text(E->AsObject(),TEXT("id"))); break; } } MarkComposer(true); })];
        if (Kind==TEXT("add_effect")) BuildEffect(ActionBox,Object(Action,TEXT("effect")),true);
        else
        {
            ActionBox->AddSlot().AutoHeight().Padding(0,6)[EffectPicker(SelectedAbility,Text(Action,TEXT("effectId")),[this,Action](FString V) { Action->SetStringField(TEXT("effectId"),V); MarkComposer(true); })];
            ActionBox->AddSlot().AutoHeight()[NumericField(Kind==TEXT("percent") ? TEXT("Percent (+25 increases; −25 decreases)") : TEXT("Flat amount"),Number(Action,TEXT("value"))*(Kind==TEXT("percent") ? 100 : 1),[this,Action,Kind](double V) { Action->SetNumberField(TEXT("value"),V/(Kind==TEXT("percent") ? 100 : 1)); MarkComposer(); })];
        }
        ActionBox->AddSlot().AutoHeight().Padding(0,8)[Button(TEXT("Remove action"),[this,Rule,Action] { Remove(Rule,TEXT("actions"),Action); MarkComposer(true); })];
        Box->AddSlot().AutoHeight().Padding(0,0,0,8)[SNew(SBorder).Padding(8)[ActionBox]];
    }
    Box->AddSlot().AutoHeight()[Button(TEXT("+ Additional effect"),[this,Rule] { auto Action=Parse(TEXT("{\"kind\":\"add_effect\"}")); Action->SetObjectField(TEXT("effect"),DefaultEffect(TEXT("status"))); Append(Rule,TEXT("actions"),Action); MarkComposer(true); })];
    Box->AddSlot().AutoHeight().Padding(0,8)[Button(TEXT("Remove rule"),[this,Rule] { Remove(Composer,TEXT("conditions"),Rule); MarkComposer(true); })];
}
void SWarAbilityWorkshop::BuildSpecialPage()
{
    if (!SpecialPage || !Store.IsValid()) return; SpecialPage->ClearChildren(); const auto W=Store->Document().Get();
    if (Tab==TEXT("Version History"))
    {
        SpecialPage->AddSlot().AutoHeight()[Label(TEXT("Personal GM session · deployment"))];
        SpecialPage->AddSlot().AutoHeight().Padding(0,10)[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).Text_Lambda([this] { return FText::FromString(Store->DeploymentStatus()); })];
        auto PersonalActions=SNew(SHorizontalBox);
        PersonalActions->AddSlot().AutoWidth()[Button(TEXT("Deploy draft to this game"),[this] {
            if (bDirtyComposer) { Notice=TEXT("Apply or discard the open composer changes before deploying."); return; }
            if (Store->PersonalPending()) { Notice=TEXT("Wait for the pending deployment to finish."); return; }
            Notice=Store->ApplyToDevelopment(Owner.Get()) ? TEXT("Complete version staged. Waiting for the next simulation tick.") : Store->GetMessage();
        })];
        PersonalActions->AddSlot().AutoWidth().Padding(8,0)[Button(TEXT("Restore shipped abilities"),[this] {
            if (Store->PersonalPending()) { Notice=TEXT("Wait for the pending deployment to finish."); return; }
            Notice=Store->RestoreShipped(Owner.Get()) ? TEXT("Shipped abilities staged for future casts.") : Store->GetMessage();
        })];
        SpecialPage->AddSlot().AutoHeight()[PersonalActions];
        SpecialPage->AddSlot().AutoHeight().Padding(0,10)[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).Text(FText::FromString(TEXT("Deploys to your authorized local development game and restores on your next GM launch. Existing casts, statuses, resources and cooldowns retain their state. Your editable draft stays separate from deployment history.")))];
        for (const auto& V:Store->PersonalHistory()) {
            const auto D=V->AsObject(); const FString Version=Text(D,TEXT("versionId"));
            auto Row=SNew(SHorizontalBox);
            Row->AddSlot().FillWidth(1)[Label(Text(D,TEXT("createdAt"))+TEXT(" · ")+Text(D,TEXT("name"))+TEXT(" · ")+Version.Left(8)+TEXT(" · ")+Text(D,TEXT("phase")))];
            Row->AddSlot().AutoWidth()[Button(TEXT("Deploy this version"),[this,Version] {
                if (Store->PersonalPending()) { Notice=TEXT("Wait for the pending deployment to finish."); return; }
                Notice=Store->RollbackPersonal(Owner.Get(),Version) ? TEXT("Saved version staged for future casts.") : Store->GetMessage();
            })];
            SpecialPage->AddSlot().AutoHeight().Padding(0,4)[Row];
        }
        SpecialPage->AddSlot().AutoHeight().Padding(0,10)[Button(TEXT("Validate personal deployment"),[this] { FString Error;
            Notice=Store->ValidatePersonal(Store->Document().Get(),Error) ? TEXT("Definitions, compatibility and changed assignment presentations passed validation.") : Error; })];
        BuildReview();
        SpecialPage->AddSlot().AutoHeight().Padding(0,20)[Label(TEXT("Shared publication · admission gates remain closed"))];
        SpecialPage->AddSlot().AutoHeight().Padding(0,10)[Field(TEXT("Target environment"),Store->GetEnvironment(),[this](FString V) { if (!Store->SetEnvironment(V)) Notice=TEXT("Invalid environment or pending request."); })];
        SpecialPage->AddSlot().AutoHeight()[Field(TEXT("Workspace ID (load for conflict comparison)"),Text(W,TEXT("id")),[this](FString Id) { Store->LoadShared(Id); })];
        SpecialPage->AddSlot().AutoHeight().Padding(0,10)[Button(TEXT("Validate definitions and presentations"),[this] { TArray<FWarAbilityDefinition> Definitions; FString Error;
            Notice=FWarAbilityWorkshopDocument::Compile(Store->Document().Get(),Definitions,Error) && Store->ValidatePresentations(Definitions,Error) ? TEXT("Local definitions and loaded presentation bindings passed validation.") : Error; })];
        SpecialPage->AddSlot().AutoHeight()[Button(TEXT("Publish saved revision as immutable version"),[this] { Store->Publish(TEXT("Ability workshop revision")); })];
        SpecialPage->AddSlot().AutoHeight().Padding(0,10)[SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(TEXT("Shared publication and deployment remain closed until native shared admission and GM authority are verified. A saved draft is not a published version. Existing activations retain their captured definitions.")))];
        SpecialPage->AddSlot().AutoHeight()[Button(TEXT("Refresh versions / deployments"),[this] { Store->RefreshHistory(); })];
        for (const auto& V:Store->History()) { const auto Version=V->AsObject(); SpecialPage->AddSlot().AutoHeight().Padding(0,10)[Label(Text(Version,TEXT("name"))+TEXT(" · ")+Text(Version,TEXT("id")))]; }
        for (const auto& V:Store->Deployments()) { const auto D=V->AsObject(); SpecialPage->AddSlot().AutoHeight().Padding(0,6)[Label(TEXT("Deployment ")+Text(D,TEXT("id"))+TEXT(" · ")+Text(D,TEXT("phase")))]; }
        if (Store->Conflict())
        {
            SpecialPage->AddSlot().AutoHeight().Padding(0,12)[Label(TEXT("Base / current / yours · resolve each conflicting field"))];
            for (const auto& C:Store->Conflicts())
            {
                const auto Describe=[](const TSharedPtr<FJsonValue>& Value) { if (!Value) return FString(TEXT("<deleted>")); auto J=MakeShared<FJsonObject>(); J->SetField(TEXT("value"),Value); return Serialize(J).Left(700); };
                SpecialPage->AddSlot().AutoHeight().Padding(0,10)[SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(C.Path+TEXT("\nBase: ")+Describe(C.Base)+TEXT("\nCurrent: ")+Describe(C.Current)+TEXT("\nYours: ")+Describe(C.Yours)))];
                SpecialPage->AddSlot().AutoHeight()[Button(TEXT("Use current"),[this,Path=C.Path] { Store->ResolveConflict(Path,false); BuildSpecialPage(); })];
                SpecialPage->AddSlot().AutoHeight()[Button(TEXT("Use yours"),[this,Path=C.Path] { Store->ResolveConflict(Path,true); BuildSpecialPage(); })];
            }
            SpecialPage->AddSlot().AutoHeight().Padding(0,12)[Button(TEXT("Commit merged draft"),[this] { Store->CommitMerge(); BuildSpecialPage(); })];
        }
    }
    else
    {
        SpecialPage->AddSlot().AutoHeight()[Label(TEXT("Test Arena · native admission required"))];
        SpecialPage->AddSlot().AutoHeight().Padding(0,12)[SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(TEXT("The online arena requires a separately admitted authoritative session and approved character assets. No arena session is currently connected; this workspace has no measured test evidence. Editing the draft invalidates evidence for earlier revisions.")))];
        SpecialPage->AddSlot().AutoHeight()[Label(TEXT("Definition validation is available in Review & Publish. Calculated condition checks do not count as measured combat results."),true)];
        BuildScenario();
    }
}
