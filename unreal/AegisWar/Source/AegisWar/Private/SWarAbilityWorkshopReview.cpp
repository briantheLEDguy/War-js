#include "SWarAbilityWorkshop.h"
#include "WarAbilityWorkshopSubsystem.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Text/STextBlock.h"

using namespace WarWorkshopJson;
bool SWarAbilityWorkshop::VerifyReview(FString& Error)
{
    if (!Store.IsValid()) return false;
    FString Version; const auto Baseline=Store->ReviewBaseline(Version,Error);
    if (!Baseline) return false;
    const auto Changes=FWarAbilityWorkshopDocument::Changes(Baseline,Store->Document().Get());
    if (!Changes.ContainsByPredicate([](const auto& C) { return C.Path.Contains(TEXT("/conditions")); }))
    { Error=TEXT("Review did not include the committed conditional example."); return false; }
    Tab=TEXT("Version History"); ReviewPage=0; Build(); return true;
}
namespace
{
    FString Describe(const TSharedPtr<FJsonValue>& Value)
    {
        if (!Value) return TEXT("Not present");
        if (Value->Type==EJson::String) return Value->AsString();
        if (Value->Type==EJson::Number) return FString::SanitizeFloat(Value->AsNumber(),0);
        if (Value->Type==EJson::Boolean) return Value->AsBool() ? TEXT("Yes") : TEXT("No");
        auto Wrapper=MakeShared<FJsonObject>(); Wrapper->SetField(TEXT("value"),Value); const FString Json=Serialize(Wrapper);
        return Json.Mid(9,Json.Len()-10);
    }
    void References(const TSharedPtr<FJsonObject>& Node,TSet<FString>& Out)
    {
        if (!Node) return;
        const FString Id=Text(Node,TEXT("abilityId"));
        if (!Id.IsEmpty()) Out.Add(Id+(Text(Node,TEXT("effectId")).IsEmpty() ? TEXT("") : TEXT(" / ")+Text(Node,TEXT("effectId"))));
        for (const auto& Child:Array(Node,TEXT("children"))) References(Child->AsObject(),Out);
    }
    FString HumanPath(const FString& Path,const TSharedPtr<FJsonObject>& Draft,const TSharedPtr<FJsonObject>& Baseline)
    {
        TArray<FString> Parts; Path.ParseIntoArray(Parts,TEXT("/"));
        TSharedPtr<FJsonObject> Ability;
        if (Parts.Num()>1 && Parts[0]==TEXT("abilities")) { Ability=Find(Draft,TEXT("abilities"),Parts[1]); if (!Ability) Ability=Find(Baseline,TEXT("abilities"),Parts[1]); Parts[0]=TEXT("Shared base"); Parts[1]=Text(Ability,TEXT("name")); }
        else if (Parts.Num()>1) for (const auto& V:Array(Draft,TEXT("abilities"))) if (Text(V->AsObject(),TEXT("name"))==Parts[1].TrimStartAndEnd()) { Ability=V->AsObject(); break; }
        const TMap<FString,FString> Names{{TEXT("effective"),TEXT("Effective ability")},{TEXT("conditions"),TEXT("Conditions")},{TEXT("condition"),TEXT("IF")},{TEXT("children"),TEXT("Checks")},{TEXT("actions"),TEXT("THEN")},{TEXT("kind"),TEXT("Type")},{TEXT("value"),TEXT("Bonus value")},{TEXT("effectId"),TEXT("Effect")},{TEXT("abilityId"),TEXT("Ability")},{TEXT("source"),TEXT("Applied by")},{TEXT("subject"),TEXT("Subject")},{TEXT("event"),TEXT("Check at")},{TEXT("not"),TEXT("IS NOT")},{TEXT("name"),TEXT("Name")},{TEXT("id"),TEXT("Identity")},{TEXT("amount"),TEXT("Amount")},{TEXT("min"),TEXT("Minimum")},{TEXT("max"),TEXT("Maximum")},{TEXT("cooldownSec"),TEXT("Cooldown (s)")},{TEXT("durationSec"),TEXT("Duration (s)")},{TEXT("intervalSec"),TEXT("Interval (s)")},{TEXT("unlockLevel"),TEXT("Unlock level")},{TEXT("displayOrder"),TEXT("Display order")},{TEXT("overrides"),TEXT("Class overrides")},{TEXT("@order"),TEXT("Order")}};
        for (auto& Part:Parts) { Part.TrimStartAndEndInline(); const auto Rule=Find(Ability,TEXT("conditions"),Part); if (Rule) Part=Text(Rule,TEXT("name")); else if (const auto* Name=Names.Find(Part)) Part=*Name; }
        return FString::Join(Parts,TEXT(" / "));
    }
}
void SWarAbilityWorkshop::BuildReview()
{
    FString Version,Error; const auto Baseline=Store->ReviewBaseline(Version,Error),Draft=Store->Document().Get();
    const auto Wrapped=[this](const FString& Value) { return SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).Text(FText::FromString(Value)); };
    if (!Baseline) { SpecialPage->AddSlot().AutoHeight()[Wrapped(TEXT("Cannot compare active definitions: ")+Error)]; return; }
    SpecialPage->AddSlot().AutoHeight().Padding(0,16,0,6)[Wrapped(TEXT("Before / after · this session's active catalog ")+Version+TEXT(" → draft r")+FString::SanitizeFloat(Number(Draft,TEXT("revision")),0))];
    SpecialPage->AddSlot().AutoHeight()[Wrapped(TEXT("This comparison uses the connected session's catalog. It does not attest that another environment has the same active version."))];
    TArray<FWarWorkshopChange> Changes;
    TSet<FString> ChangedAbilities,AffectedClasses,AssignmentIds;
    auto Before=MakeShared<FJsonObject>(),After=MakeShared<FJsonObject>();
    Before->SetArrayField(TEXT("abilities"),Array(Baseline,TEXT("abilities"))); After->SetArrayField(TEXT("abilities"),Array(Draft,TEXT("abilities")));
    Changes=FWarAbilityWorkshopDocument::Changes(Before,After);
    for (const auto& Change:Changes) { TArray<FString> Parts; Change.Path.ParseIntoArray(Parts,TEXT("/")); if (Parts.Num()>1) ChangedAbilities.Add(Parts[1]); }
    for (const auto& W:{Baseline,Draft}) for (const auto& Value:Array(W,TEXT("assignments"))) AssignmentIds.Add(Text(Value->AsObject(),TEXT("id")));
    TArray<FString> OrderedIds=AssignmentIds.Array(); OrderedIds.Sort(); int32 AffectedAssignments=0;
    for (const auto& Id:OrderedIds)
    {
        const auto B=Find(Baseline,TEXT("assignments"),Id),A=Find(Draft,TEXT("assignments"),Id);
        const auto EffectiveBefore=B ? FWarAbilityWorkshopDocument::Effective(Baseline,B,Error) : nullptr;
        const auto EffectiveAfter=A ? FWarAbilityWorkshopDocument::Effective(Draft,A,Error) : nullptr;
        auto Left=B ? Clone(B) : nullptr,Right=A ? Clone(A) : nullptr;
        if (Left) Left->SetObjectField(TEXT("effective"),EffectiveBefore);
        if (Right) Right->SetObjectField(TEXT("effective"),EffectiveAfter);
        auto AssignmentChanges=FWarAbilityWorkshopDocument::Changes(Left,Right);
        if (AssignmentChanges.IsEmpty()) continue;
        ++AffectedAssignments;
        const auto Assignment=A ? A : B; const FString ClassId=Text(Assignment,TEXT("classId"));
        const FString ClassName=Text(Find(Draft,TEXT("classes"),ClassId),TEXT("name")); AffectedClasses.Add(ClassName);
        const FString AbilityId=Text(Assignment,TEXT("abilityId")); const auto Ability=Find(A ? Draft : Baseline,TEXT("abilities"),AbilityId);
        for (auto& Change:AssignmentChanges) { Change.Path=ClassName+TEXT(" / ")+Text(Ability,TEXT("name"))+Change.Path; Changes.Add(MoveTemp(Change)); }
    }
    TArray<FString> ClassNames=AffectedClasses.Array(); ClassNames.Sort();
    SpecialPage->AddSlot().AutoHeight().Padding(0,10)[Wrapped(FString::Printf(TEXT("%d affected assignments · %d classes · %d changed fields\n"),AffectedAssignments,ClassNames.Num(),Changes.Num())+FString::Join(ClassNames,TEXT(", ")))];
    TSet<FString> Dependencies;
    for (const auto& Value:Array(Draft,TEXT("abilities"))) {
        const auto A=Value->AsObject();
        for (const auto& RuleValue:Array(A,TEXT("conditions"))) { const auto Rule=RuleValue->AsObject(); TSet<FString> Refs; References(Object(Rule,TEXT("condition")),Refs);
            for (const auto& Ref:Refs) { FString AbilityId,Effect; if (!Ref.Split(TEXT(" / "),&AbilityId,&Effect)) AbilityId=Ref;
                if (ChangedAbilities.Contains(Text(A,TEXT("id"))) || ChangedAbilities.Contains(AbilityId)) Dependencies.Add(Text(A,TEXT("name"))+TEXT(" / ")+Text(Rule,TEXT("name"))+TEXT(" → ")+Ref); }
        }
    }
    TArray<FString> DependencyNames=Dependencies.Array(); DependencyNames.Sort();
    SpecialPage->AddSlot().AutoHeight().Padding(0,8)[Wrapped(TEXT("Conditional dependencies: ")+(DependencyNames.IsEmpty() ? TEXT("No changed dependencies") : FString::Join(DependencyNames,TEXT("; "))))];
    SpecialPage->AddSlot().AutoHeight().Padding(0,8)[Wrapped(TEXT("Test evidence: no authoritative arena result is attached to this exact draft. Calculated previews do not satisfy measured test evidence."))];
    const int32 Pages=FMath::Max(1,FMath::DivideAndRoundUp(Changes.Num(),30)); ReviewPage=FMath::Clamp(ReviewPage,0,Pages-1);
    auto Paging=SNew(SHorizontalBox);
    Paging->AddSlot().AutoWidth()[Button(TEXT("Previous changes"),[this] { ReviewPage=FMath::Max(0,ReviewPage-1); BuildSpecialPage(); })];
    Paging->AddSlot().AutoWidth().Padding(12,6)[Label(FString::Printf(TEXT("Page %d / %d"),ReviewPage+1,Pages))];
    Paging->AddSlot().AutoWidth()[Button(TEXT("Next changes"),[this] { ++ReviewPage; BuildSpecialPage(); })];
    SpecialPage->AddSlot().AutoHeight().Padding(0,10)[Paging];
    const auto Row=[&](const FString& Field,const FString& B,const FString& A) {
        auto Cells=SNew(SHorizontalBox);
        for (const auto& TextValue:{Field,B,A}) Cells->AddSlot().FillWidth(1).Padding(8,6)[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).Text(FText::FromString(TextValue.Left(600))).ToolTipText(FText::FromString(TextValue))];
        return Cells;
    };
    SpecialPage->AddSlot().AutoHeight()[Row(TEXT("Class / ability / field"),TEXT("Before"),TEXT("After"))];
    for (int32 I=ReviewPage*30;I<FMath::Min(Changes.Num(),(ReviewPage+1)*30);++I) {
        const auto& Change=Changes[I]; SpecialPage->AddSlot().AutoHeight().Padding(0,1)[SNew(SBorder).Padding(0)[Row(HumanPath(Change.Path,Draft,Baseline),Describe(Change.Before),Describe(Change.After))]];
    }
}
